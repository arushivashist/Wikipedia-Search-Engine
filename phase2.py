import math
import os
import re
import sys

from datetime import datetime
from nltk.stem.porter import PorterStemmer


porter_stemmer = PorterStemmer()

query_re = re.compile(r'[b|c|e|i|r|t]:')

stop_words = {}
with open('stop_words') as f:
	words = f.readlines()
	for x in range(len(words)):
		stop_words[words[x].strip()] = True

def calc_tfidf(documents):
	tf_idf = {}
	for key in documents:
		docs_present = len(documents[key])
		if docs_present:
			idf = math.log10(float(DOC_CTR)/docs_present)
			for doc in documents[key]:
				tf = 1.0 + math.log10(float(documents[key][doc]))
				temp_tfidf = tf * idf
				if tf_idf.has_key(doc):
					tf_idf[doc] += temp_tfidf
				else:
					tf_idf[doc] = temp_tfidf

	tf_idf = sorted(tf_idf.items(), key=lambda x:x[1], reverse=True)[:10]
	doc_title = {}
	for val in tf_idf:
		doc_title[val[0]] = None

	for val in tf_idf:
		docid = int(val[0])
		with open("docid_title_map-" + str(docid/1000), "rb") as f:
			for line in f:
				line = line.strip().split(":")
				if line[0] == val[0]:
					print line[0], line[1]

def field_query(query):
	query = query.split()
	new_query = []
	new_fields = []
	fields = ['b:', 'c:', 'e:', 'i:', 'r:', 't:']
	last = None
	for key in query:
		if key in fields:
			last = key[0]
		elif key not in stop_words:
			new_query.append(key)
			new_fields.append(last)

	documents = {}
	for x in range(len(new_query)):
		first_char = new_query[x][0]
		filename = "final_index-" + first_char + "-" + new_fields[x]
		temp_dict = {}
		if os.path.exists(filename):
			with open(filename, "rb") as f:
				for line in f:
					line = line.split(";")
					if line[0] == new_query[x]:
						temp_docs = line[1].strip().split(",")
						for doc in temp_docs:
							doc = doc.split(":")
							temp_dict[doc[0]] = doc[1]
			documents[new_query[x]] = temp_dict

	calc_tfidf(documents)

def normal_query(query):
	query = query.split()
	documents = {}
	fields = ['b', 'c', 'e', 'i', 'r', 't']
	for key in query:
		temp_dict = {}
		first_char = key[0]
		for fld in fields:
			filename = "final_index-" + first_char + "-" + fld
			if os.path.exists(filename):
				with open(filename, "rb") as f:
					for line in f:
						line = line.split(";")
						if line[0] == key:
							temp_docs = line[1].strip().split(",")
							for doc in temp_docs:
								doc = doc.split(":")
								if temp_dict.has_key(doc[0]):
									temp_dict[doc[0]] += int(doc[1])
								else:
									temp_dict[doc[0]] = int(doc[1])
		documents[key] = temp_dict

	calc_tfidf(documents)

DOC_CTR = 0
with open("docid_ctr", "rb") as f:
	DOC_CTR = int(f.read().strip())

while True:
	try:
		query = raw_input(">>> Enter search query: ")
		query = query.lower()
		start_time = datetime.now()
		if query_re.search(query):
			field_query(query)
		else:
			normal_query(query)
		print "Time taken to execute query: ", datetime.now() - start_time
	except EOFError:
		sys.exit()
