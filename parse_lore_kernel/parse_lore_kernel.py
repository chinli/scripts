#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import os
import sys
import getopt
import requests
import xlwt
from datetime import datetime

VERSION="v2023.8.22"

url_path="https://lore.kernel.org/all/"
report_file="result.xlsx"

def usage():
	"""
The script is  parse the url of lore.kernel.org to get submitter information of Amlogic,
Usage: ./parse_lore_kernel.py -f <Mail domain> -y 2023
default output file is result.txt

Example: ./parse_lore_kernel.py -f gmail.com -y 2023
Note: This script is depend on requests and xlwt library, install cmd is "pip3 install requests xlwt"

Description
	-h --help			display help information
	-f <Mail domain>	match within the From header
	-o <report_file>	report file of results
	-y <year>			assign the year
	-s <start_date>		format like 2023-01-01
	-e <end_date>		format like 2023-06-30
	-m <target_month>	assign the year-month, like 2023-07
	-v --version		version information
"""

def is_date_between(start_date, end_date, target_date):
    return start_date <= target_date <= end_date

def extract_substring(main_string, start_marker, end_marker):
	start_index = main_string.find(start_marker)
	end_index = main_string.find(end_marker, start_index + len(start_marker))

	if start_index != -1 and end_index != -1:
		extracted_substring = main_string[start_index + len(start_marker):end_index]
		return extracted_substring
	else:
		return None

def write_sheet(book, sheet_name, list_name):
	sheet = book.add_sheet(sheet_name)
	sheet.write(0, 0, "ID")#write the id
	sheet.write(0, 1, "Subject")#write the subject name
	sheet.write(0, 2, "Link")#write the Link url
	sheet.write(0, 3, "Author")#write the author
	sheet.write(0, 4, "Date")#write the date
	row = 1
	for info in list_name:
		sheet.write(row, 0, row)#write the id
		sheet.write(row, 1, info[0])#write the subject name
		sheet.write(row, 2, info[1])#write the Link url
		sheet.write(row, 3, info[2])#write the author
		sheet.write(row, 4, info[3])#write the date
		row += 1
#		print("subject:", info[0])

def get_title(http_resp, start_date, end_date):
	lines = http_resp.split("\n")
	title_list = []
	total_list = []
	line_index = 0
	continue_flag = 0
	for line in lines:
		if "[PATCH" in line:
			title = extract_substring(line, "\">", "</a>")
			link = "https://lore.kernel.org/all/" + extract_substring(line, "href=\"", "/\">")
			line_index=lines.index(line)
			author = extract_substring(lines[line_index+1], "by ", " @")
			date = extract_substring(lines[line_index+1], "@ ", " [")
			this_date = datetime.strptime(date, "%Y-%m-%d %H:%M %Z").date()
			if is_date_between(start_date, end_date, this_date):
				title_list.append(title)
				title_list.append(link)
				title_list.append(author)
				title_list.append(date)
				total_list.append(title_list)
				title_list = []
				continue_flag = 1
			else:
				continue_flag = 0

	return total_list, continue_flag

if __name__ == '__main__':
	opt_flag = ""
	try:
		opts, args = getopt.getopt(sys.argv[1:], "f:o:y:s:e:m:hv", ["help","version"])
	except getopt.GetoptError as err:
		print(err)
		print(usage.__doc__)
		sys.exit(2)
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			print(usage.__doc__)
			sys.exit()
		elif opt in ("-f"):
			from_header = arg
			url_path = url_path + "?q=f:" + from_header
			print("Current url path:"+url_path)
		elif opt in ("-o"):
			report_file = arg
		elif opt in ("-y"):
			target_year_str = arg.strip(" ")
			opt_flag = "one_year"
		elif opt in ("-s"):
			opt_flag = "between"
			start_date_str = arg.strip(" ")
		elif opt in ("-e"):
			opt_flag = "between"
			end_date_str = arg.strip(" ")
		elif opt in ("-m"):
			opt_flag = "one_month"
			target_month_str = arg.strip(" ")
		elif opt in ("-v", "--version"):
			print(VERSION)
			sys.exit()
		else:
			print("Using the wrong way, please refer the help information!")
			assert False, "unhandled option"

	if opt_flag == "one_year":
		start_date = datetime.strptime(target_year_str + "-01-01", "%Y-%m-%d").date()
		end_date = datetime.strptime(target_year_str + "-12-31", "%Y-%m-%d").date()
		search_date = target_year_str + "-01-01.." + target_year_str + "-12-31"
		report_file = target_year_str + "_result.xlsx"
	elif opt_flag == "between":
		search_date = start_date_str + ".." + end_date_str
		start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
		end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
		report_file = start_date_str + "_" + end_date_str + "_result.xlsx"
	elif opt_flag == "one_month":
		start_date = datetime.strptime(target_month_str + "-01", "%Y-%m-%d").date()
		end_date = datetime.strptime(target_month_str + "-31", "%Y-%m-%d").date()
		search_date = target_month_str + "-01.." + target_month_str + "-31"
		report_file = target_month_str + "_result.xlsx"
	else:
		print( "Pls input date parameter!")
		print(usage.__doc__)
		sys.exit()

	page_total_list = []
	total_list = []
	title_only_list = []
	new_total_list = []
	submission_list = []
	replay_list = []
	review_list = []
	page_index = 0
	while 1:
		req_url = url_path + "+d%3A"+ search_date + "&o=" + str(page_index)
		print("req_url:"+req_url)
		resp = requests.get(req_url)
		if resp.status_code == 200:
			[page_total_list, flag] = get_title(resp.text, start_date, end_date)
			print("page_total_list count:", len(page_total_list))
			total_list += page_total_list
			#check target month is over or not
			if flag:
				page_index += 200 #each request for 200 items
			else:
				break
		else:
			print("http request filed!")
			sys.exit(2)

	#split replay and submission
	for info in total_list:
		if info[0] not in title_only_list:
			title_only_list.append(info[0])
			new_total_list.append(info)

	for info in new_total_list:
		if "Re: " in info[0]:
			replay_list.append(info)
		else:
			submission_list.append(info)

	for info1 in replay_list:
		flag = 0
		for info2 in submission_list:
			if info2[0] in info1[0]:
				flag = 1
				break;
		if (flag == 0): #replay is not in submission list
			review_list.append(info1)

	print("Results as below:")
	print("total_list count:", len(new_total_list))
	print("submission_list:", len(submission_list))
	print("replay_list:", len(replay_list))
	print("review_list:", len(review_list))

	#write the total result to excel file
	book = xlwt.Workbook(encoding='utf-8', style_compression=0)
	write_sheet(book, "Total", new_total_list)

	#write the submission result to excel file
	write_sheet(book, "Submission", submission_list)

	#write the replay result to excel file
	write_sheet(book, "Reply", replay_list)

	#write the review result to excel file
	write_sheet(book, "Review", review_list)

	book.save(report_file)

