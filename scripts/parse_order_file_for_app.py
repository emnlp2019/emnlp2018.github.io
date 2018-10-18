#!/usr/bin/env python3

'''
This script parses the following four input files provided by the program chairs
and generates the various files needed to build the schedule in the conference app.

- order.txt
- authors.csv
- session-chairs.csv
- abstracts.csv

Note that `dos2unix` must be run on the order file before processing.

'''

import argparse
import csv
import logging

from datetime import datetime
from itertools import count

from parse_order_file_and_generate_schedule import (NON_PAPER_SESSION_REGEXP,
                                                    BREAK_SESSION_REGEXP,
                                                    PAPER_SESSION_GROUP_REGEXP,
                                                    PAPER_SESSION_REGEXP,
                                                    PAPER_REGEXP,
                                                    POSTER_DEMO_REGEXP,
                                                    BEST_PAPER_REGEXP,
                                                    KEYNOTE_ABSTRACT_DICT,
                                                    process_line,
                                                    collect_instances)


def main():

    # set up an argument parser
    parser = argparse.ArgumentParser(prog='parse_order_file_and_generate_schedule.py')
    parser.add_argument("--order",
                        dest="order_file",
                        required=True,
                        help="Path to order file containing session information")
    parser.add_argument("--authors",
                        dest="authors_csv",
                        required=True,
                        help="Path to CSV file containing author information")
    parser.add_argument("--chairs",
                        dest="chairs_csv",
                        required=True,
                        help="Path to CSV file containing session chair information")
    parser.add_argument("--abstracts",
                        dest="abstracts_csv",
                        required=True,
                        help="Path to CSV file containing the abstracts")

    # parse given command line arguments
    args = parser.parse_args()

    # set up the logging
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    # open order file and capture the contents of each day into separate lists
    with open(args.order_file, 'r') as orderfh:
        processed_lines = [process_line(line) for line in orderfh]
    days = collect_instances(iter(processed_lines), '*')

    # read in the CSV file mapping paper IDs to authors
    authors_dict = {}
    with open(args.authors_csv, 'r') as authorsfh:
        reader = csv.DictReader(authorsfh, fieldnames=["Submission ID", "Authors"])
        for row in reader:
            assert row['Submission ID'] not in authors_dict
            authors_dict[row['Submission ID']] = row['Authors']

    # read in the CSV file mapping sessions to chairs
    chairs_dict = {}
    with open(args.chairs_csv, 'r') as chairsfh:
        reader = csv.DictReader(chairsfh, fieldnames=["Session", "Name", "Email"])
        for row in reader:
            session_id = row['Session'].split(':')[0]
            assert session_id not in chairs_dict
            chairs_dict[session_id] = (row['Name'], row['Email'])

    # read in the CSV file mapping paper IDs to abstracts
    abstract_dict = {}
    with open(args.abstracts_csv, 'r') as abstractsfh:
        reader = csv.DictReader(abstractsfh, fieldnames=["Paper ID", "Abstract"])
        for row in reader:
            abstract_dict[row['Paper ID']] = row['Abstract']

    # set up the files we need to write to
    sessionsfh = open('data/app/sessions.csv', 'a')
    session_csv_writer = csv.writer(sessionsfh)

    papersfh = open('data/app/papers.csv', 'w')
    paper_csv_writer = csv.writer(papersfh)
    paper_csv_writer.writerow(["Session ID", "Presentation ID", "Session Title", "Date", "Time Start", "Time End", "Room/Location", "Schedule Track", "Description"])

    # we have the tutorial and keynote authors pre-populated
    # in this CSV file so first let's read those into a dictionary
    # so that we don't mistakenly assign these authors new IDs
    with open('data/app/authors.csv', 'r') as authors_infh:
        reader = csv.DictReader(authors_infh,
                                fieldnames=['Presentation ID', 'Author ID', 'Name'])
        app_author_id_dict = {}
        for row in reader:
            app_author_id_dict[row['Name']] = row['Author ID']

    # and now open the file in append mode since we will be appending
    # new authors to this file
    authorsfh = open('data/app/authors.csv', 'a')
    author_csv_writer = csv.writer(authorsfh)

    linkingfh = open('data/app/linking.csv', 'a')
    linking_csv_writer = csv.writer(linkingfh)

    app_id_counter = count(start=45)

    # now in each day, process each session one by one
    for day in days:
        day_string = day.pop(0).lstrip('* ')

        day_datetime = datetime.strptime(day_string, '%A, %d %B %Y')

        # take the days's contents and group them into sessions
        day_sessions = collect_instances(iter(day), '+')

        # now iterate over each session in the day
        for session in day_sessions:
            session_string = session.pop(0).lstrip('+ ').strip()
            if 'break' in session_string.lower() or 'lunch' in session_string.lower():
                session_start, session_end, break_title = BREAK_SESSION_REGEXP.match(session_string).groups()
                if break_title.lower() == 'lunch':
                    break_title = 'Lunch'
                else:
                    break_title = 'Coffee Break'
                session_csv_writer.writerow([next(app_id_counter), break_title, day_datetime.strftime('%D'), session_start, session_end, '', 'Conference Sessions', ''])
            elif 'keynote' in session_string.lower():
                session_start, session_end, session_title, session_location = NON_PAPER_SESSION_REGEXP.match(session_string).groups()
                if 'Julia' in session_title:
                    session_title = session_title.replace('Julia Hirschberg ', '')
                    session_abstract = KEYNOTE_ABSTRACT_DICT['Julia']
                    session_people = 'Julia Hirschberg (Columbia University)'
                    session_people_link = 'http://www.cs.columbia.edu/~julia/'
                elif 'Gideon' in session_title:
                    session_title = session_title.replace('Gideon Mann ', '')
                    session_abstract = KEYNOTE_ABSTRACT_DICT['Gideon']
                    session_people = 'Gideon Mann (Bloomberg, L.P.)'
                    session_people_link = 'https://sites.google.com/site/gideonmann/'
                elif 'Johan' in session_title:
                    session_title = session_title.replace('Johan Bos ', '')
                    session_abstract = KEYNOTE_ABSTRACT_DICT['Johan']
                    session_people = 'Johan Bos (University of Groningen)'
                    session_people_link = 'https://www.rug.nl/staff/johan.bos/'
                session_csv_writer.writerow([next(app_id_counter), session_title, day_datetime.strftime('%D'), session_start, session_end, session_location, 'Conference Sessions', session_abstract])
            elif 'opening' in session_string.lower():
                session_start, session_end, session_title, session_location = NON_PAPER_SESSION_REGEXP.match(session_string).groups()
                session_csv_writer.writerow([next(app_id_counter), session_title, day_datetime.strftime('%D'), session_start, session_end, session_location, 'Conference Sessions', ''])
            elif 'social event' in session_string.lower():
                session_start, session_end, session_title, session_location = NON_PAPER_SESSION_REGEXP.match(session_string).groups()
                session_csv_writer.writerow([next(app_id_counter), session_title, day_datetime.strftime('%D'), session_start, session_end, 'Royal Museums of Fine Arts of Belgium', 'Conference Sessions', 'On the evening of Saturday, November 3rd, the EMNLP 2018 social event will take place at the Royal Museums of Fine Arts of Belgium. Four museums, housed in a single building, will welcome the EMNLP delegates with their prestigious collection of 20,000 works of art. The Museums’ collections trace the history of the visual arts — painting, sculpture and drawing — from the 15th to the 21st century.'])
            elif 'business meeting' in session_string.lower():
                session_start, session_end, session_title, session_location = NON_PAPER_SESSION_REGEXP.match(session_string).groups()
                session_csv_writer.writerow([next(app_id_counter), session_title, day_datetime.strftime('%D'), session_start, session_end, session_location, 'Conference Sessions', 'All attendees are strongly encouraged to participate in the business meeting.'])
            elif 'best paper' in session_string.lower():
                session_start, session_end, session_title, session_location = NON_PAPER_SESSION_REGEXP.match(session_string).groups()
                app_session_id = next(app_id_counter)
                session_csv_writer.writerow([app_session_id, session_title, day_datetime.strftime('%D'), session_start, session_end, session_location, 'Conference Sessions', ''])
                for paper in session:
                    app_paper_id = next(app_id_counter)
                    best_paper_id, best_paper_start, best_paper_end, best_paper_title = BEST_PAPER_REGEXP.match(paper.strip()).groups()
                    best_paper_abstract = abstract_dict[best_paper_id]
                    paper_csv_writer.writerow([app_session_id, app_paper_id, best_paper_title, day_datetime.strftime('%D'), best_paper_start, best_paper_end, session_location, 'Main Papers & Posters', best_paper_abstract])
                    best_paper_authors = authors_dict[best_paper_id].strip()
                    best_paper_authors_list = best_paper_authors.replace(" and ", ", ").split(", ")
                    for best_paper_author in best_paper_authors_list:
                        if best_paper_author in app_author_id_dict:
                            app_author_id = app_author_id_dict[best_paper_author]
                        else:
                            app_author_id = next(app_id_counter)
                            app_author_id_dict[best_paper_author] = app_author_id
                        author_csv_writer.writerow([app_paper_id, app_author_id, best_paper_author])
                        linking_csv_writer.writerow([app_session_id, app_paper_id, app_author_id])
            elif 'orals' in session_string.lower():
                session_group_start, session_group_end, session_group_type, session_group_description, session_group_roman_numeral = PAPER_SESSION_GROUP_REGEXP.match(session_string).groups()
                session_group_type = session_group_type.replace('and', '&amp;')
                session_group_description = session_group_description.replace('and', '&amp;')
                day_session_splits = collect_instances(iter(session), '=')
                for split in day_session_splits:
                    split_string = split.pop(0).lstrip('= ').strip()
                    session_id, session_title, session_parens = PAPER_SESSION_REGEXP.match(split_string).groups()
                    session_title = session_title.replace('and', '&amp;')
                    if ',' in session_parens:
                        session_type, session_location = session_parens.split(', ')
                        session_type = session_type.strip()
                        session_location = session_location.strip()
                    else:
                        session_location = session_parens.strip()
                        session_type = ''
                    app_session_id = next(app_id_counter)
                    session_csv_writer.writerow([app_session_id, session_title, day_datetime.strftime('%D'), session_group_start, session_group_end, session_location, 'Conference Sessions', ''])
                    if 'poster' in session_type.lower() or 'poster' in session_title.lower():
                        session_title = '{} ({})'.format(session_title, session_type) if session_type else session_title
                    else:
                        session_chair_name, session_chair_email = chairs_dict[session_id]
                    for paper in split:
                        paper = paper.strip()
                        if 'poster' in session_type.lower() or 'poster' in session_title.lower():
                            if paper.startswith('@'):
                                continue
                            else:
                                poster_id, poster_title = POSTER_DEMO_REGEXP.match(paper).groups()
                                poster_abstract = abstract_dict[poster_id]
                                app_paper_id = next(app_id_counter)
                                paper_csv_writer.writerow([app_session_id, app_paper_id, poster_title, day_datetime.strftime('%D'), session_group_start, session_group_end, session_location, 'Main Papers & Posters', poster_abstract])
                                poster_authors = authors_dict[poster_id].strip()
                                poster_authors_list = poster_authors.replace(" and ", ", ").split(', ')
                                for poster_author in poster_authors_list:
                                    if poster_author in app_author_id_dict:
                                        app_author_id = app_author_id_dict[poster_author]
                                    else:
                                        app_author_id = next(app_id_counter)
                                        app_author_id_dict[poster_author] = app_author_id
                                    author_csv_writer.writerow([app_paper_id, app_author_id, poster_author])
                                    linking_csv_writer.writerow([app_session_id, app_paper_id, app_author_id])
                                if poster_id.endswith('-TACL'):
                                    poster_title = '[TACL] {}'.format(poster_title)
                        else:
                            paper_id, paper_start, paper_end, paper_title = PAPER_REGEXP.match(paper.strip()).groups()
                            paper_abstract = abstract_dict[paper_id]
                            app_paper_id = next(app_id_counter)
                            paper_csv_writer.writerow([app_session_id, app_paper_id, paper_title, day_datetime.strftime('%D'), paper_start, paper_end, session_location, 'Main Papers & Posters', paper_abstract])
                            paper_authors = authors_dict[paper_id].strip()
                            paper_authors_list = paper_authors.replace(" and ", ", ").split(', ')
                            for paper_author in paper_authors_list:
                                if paper_author in app_author_id_dict:
                                    app_author_id = app_author_id_dict[paper_author]
                                else:
                                    app_author_id = next(app_id_counter)
                                    app_author_id_dict[paper_author] = app_author_id
                                author_csv_writer.writerow([app_paper_id, app_author_id, paper_author])
                                linking_csv_writer.writerow([app_session_id, app_paper_id, app_author_id])
                            if paper_id.endswith('-TACL'):
                                paper_title = '[TACL] {}'.format(paper_title)

    # close the file handles
    sessionsfh.close()
    papersfh.close()
    authorsfh.close()
    linkingfh.close()


if __name__ == '__main__':
    main()
