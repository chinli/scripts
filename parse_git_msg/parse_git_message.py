#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import os
import sys
import getopt
import xlwt
from datetime import datetime

VERSION="v2023.4.14"
report_file="submission.xlsx"
input_file = ""
author = ""

def usage():
	"""
The script is  parse the git message with getting author/commit date/Subject,
Usage:
# cd <path of repository with kernel>
# ./parse_git_message.py -a <xxx@xxx.com>

or indicate the git message file
# ./parse_git_message.py -i log.txt

Note: This script is depend on xlwt library, install cmd is "pip3 install xlwt"

Description
	-h --help			display help information
	-a <author name>	indicate author name
	-i <input_file>		doc of git log message
	-o <report_file>	report file of results
	-v --version		version information
"""

if __name__ == '__main__':
	try:
		opts, args = getopt.getopt(sys.argv[1:], "a:i:o:hv", ["help","version"])
	except getopt.GetoptError as err:
		print(err)
		print(usage.__doc__)
		sys.exit(2)
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			print(usage.__doc__)
			sys.exit()
		elif opt in ("-a"):
			author = arg
		elif opt in ("-i"):
			input_file = arg
		elif opt in ("-o"):
			report_file = arg
		elif opt in ("-v", "--version"):
			print(VERSION)
			sys.exit()
		else:
			print("Using the wrong way, please refer the help information!")
			assert False, "unhandled option"

	
	if input_file == "":
		if author == "":
			print(usage.__doc__)
			sys.exit()

		os.system("git log --since=2017 --author=torvalds@linux-foundation.org --author="+author+" --no-merges --stat --format=\"%ncommit %H%nAuthor: %an <%ae>%nDate: %ad%nSubject: %s%n%n%b\" --output=log.txt")
		input_file = "log.txt"

	book = xlwt.Workbook(encoding='utf-8', style_compression=0)
	author_flag = 0
	release_tag_msg = 0
	commit_list = []
	total_list = []

	if os.path.exists(input_file):
		file = open(input_file, "r", errors='ignore', newline='')
		lines = file.readlines()
		changed_file = ""
		Link = ""
		sheet_names = []
		for line in lines:
			if 'commit ' in line:
				commit_id = line.split()[1]

			if 'Author: ' in line:
				author = line.split()[1:]
				author = " ".join(author)
				if "Linus Torvalds" in author:
					author_flag = 1

			if 'Date: ' in line:
				date_str = line.split()[1:]
				date_str = " ".join(date_str)
				datetime_obj = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y %z")
				date = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
				sheet_name = datetime_obj.strftime("%Y")

			if 'Subject: ' in line:
				subject = line.split()[1:]
				subject = " ".join(subject)
				if "Linux " in subject:
					release_tag_msg = 1

			if 'Link: ' in line:
				Link = line.split()[1]

			if ' | ' in line:
				changed_file += line.split()[0]+'\r\n'

			if 'file changed,' in line or 'files changed,' in line:
				#only record linus for release tag message
				if author_flag == 1:
					if release_tag_msg == 1:
						commit_list.append(commit_id)
						commit_list.append(author)
						commit_list.append(date)
						commit_list.append(subject)
						commit_list.append(Link)
						commit_list.append(changed_file)
						commit_list.append(line)
						total_list.append(commit_list)
						commit_list = []

					changed_file = ""
					Link = ""
					author_flag = 0
					release_tag_msg = 0
					continue

				#create the sheet if not exist
				try:
					sheet = book.get_sheet(sheet_name)
					row = sheet.last_used_row + 1
				except:
					sheet_names.append(sheet_name)
					sheet = book.add_sheet(sheet_name)
					col = ['id', 'commit', 'Author', 'Data', 'Subject', 'Link', 'Changed File', 'Statistics']
					for i in range(0,len(col)):
						#write the first row
						sheet.write(0, i, col[i])
						row = 1

				sheet.write(row, 0, row)#write the id
				sheet.write(row, 1, commit_id)#write the commit_id
				sheet.write(row, 2, author)#write the author
				sheet.write(row, 3, date)#write the Date
				sheet.write(row, 4, subject)#write the subject
				sheet.write(row, 5, Link)#write the Link
				sheet.write(row, 6, changed_file.rstrip('\r\n'))#write the changed file list
				sheet.write(row, 7, line.rstrip('\r\n'))#write the statistics of this commit

				#record the commit to total_list
				commit_list.append(commit_id)
				commit_list.append(author)
				commit_list.append(date)
				commit_list.append(subject)
				commit_list.append(Link)
				commit_list.append(changed_file)
				commit_list.append(line)
				total_list.append(commit_list)

				commit_list = []
				changed_file = ""
				Link = ""
				author_flag = 0
				release_tag_msg = 0
				row += 1

#add Summary sheet
sum_sheet = book.add_sheet("Summary")
sum_sheet.write(0, 0, "Year")
sum_sheet.write(0, 1, "Nr of Commit")
row = 1
for sheet_name in sheet_names:
	sum_sheet.write(row, 0, sheet_name)
	sheet = book.get_sheet(sheet_name)
	sum_sheet.write(row, 1, sheet.last_used_row)
	row += 1

#add Linus release message tag information
rls_sheet = book.add_sheet("Release")
col = ['id', 'commit', 'Author', 'Data', 'Subject', 'Link', 'Changed File', 'Statistics']
for i in range(0,len(col)):
	#write the first row
	rls_sheet.write(0, i, col[i])
	row = 1

for commit_list in total_list:
	rls_sheet.write(row, 0, row)#write the id
	rls_sheet.write(row, 1, commit_list[0])#write the commit_id
	rls_sheet.write(row, 2, commit_list[1])#write the author
	rls_sheet.write(row, 3, commit_list[2])#write the Date
	rls_sheet.write(row, 4, commit_list[3])#write the subject
	rls_sheet.write(row, 5, commit_list[4])#write the Link
	rls_sheet.write(row, 6, commit_list[5].rstrip('\r\n'))#write the changed file list
	rls_sheet.write(row, 7, commit_list[6].rstrip('\r\n'))#write the statistics of this commit
	row += 1

book.save(report_file)
print("OK! Pls Check Report File: "+report_file)
