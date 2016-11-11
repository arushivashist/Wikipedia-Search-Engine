import os
import re
import sys
import threading
import xml.sax

from heapq import heappush, heappop
from nltk.stem.porter import PorterStemmer


camelcase_re = re.compile("([A-Z]+)")
ignore_re = re.compile("[-+*/!\"#$%&\'()=~|^@`\[\]{};:<>,.?_]")
url_re = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
category_re = re.compile("Category:")
body_re = re.compile("{{.*?}}|<.*?>", re.DOTALL)

FILES = 0
FILE_CTR = 0
FILE_LIMIT = 1000

DOCID_CTR = 0
DOCID_TITLE_MAP = None

word_list = {}

porter_stemmer = PorterStemmer()

def process_word(word, elem, docId):
	new_word = porter_stemmer.stem(word)
	new_word = new_word + elem
	if word_list.has_key(new_word):
		if word_list[new_word].has_key(docId):
			word_list[new_word][docId] += 1
		else:
			word_list[new_word][docId] = 1
	else:
		word_list[new_word] = {docId: 1}

def print_content(content, elem, docId):
	for word in content:
		word = word.lower()
		if word not in stop_words:
			process_word(word, elem, docId)

def write_to_file(end=False):
	global FILES, FILE_CTR, word_list
	FILES += 1
	if end or FILES == FILE_LIMIT:
		FILES = 0
		with open("inverted_index/file" + str(FILE_CTR), "w") as f:
			for x in sorted(word_list):
				new_word = x + ";"
				temp = []
				for y in sorted(word_list[x]):
					temp.append(y + ":" + str(word_list[x][y]))
				new_word += ",".join(temp)
				f.write(new_word + "\n")
		FILE_CTR += 1
		word_list = {}

def merge_files():
	index_files = []
	for x in range(FILE_CTR):
		index_files.append("inverted_index/file" + str(x))
	open_files = []
	index_heap = []
	[open_files.append(open(file__, 'r')) for file__ in index_files]
	for file__ in open_files:
		line = file__.readline()
		word = line.split(";")[0]
		heappush(index_heap, (word, line, file__))
	while index_heap:
		smallest = heappop(index_heap)
		first_char = smallest[0][0]
		field = smallest[0].split('-')[1]
		output_filename = sys.argv[2] + '-' + first_char + '-' + field
		with open(output_filename, "ab") as f:
			f.write(smallest[1].replace("-" + field, ""))
		read_line = smallest[2].readline()
		if len(read_line) != 0:
			word = read_line.split(";")[0]
			heappush(index_heap, (word, read_line, smallest[2]))
	[file__.close() for file__ in open_files]
#	[os.remove(file__) for file__ in index_files]

stop_words = {}
with open('stop_words') as f:
	words = f.readlines()
	for x in range(len(words)):
		stop_words[words[x].strip()] = True

references_ignore = {}
with open('references_ignore') as f:
	words = f.readlines()
	for x in range(len(words)):
		references_ignore[words[x].strip()] = True

class WikiHandler(xml.sax.ContentHandler):
	def __init__(self):
		self.currElement = None
		self.innerElement = None
		self.docId = None
		self.newLine = 0
		self.title = ""
		self.references = ""
		self.body = ""

	def startElement(self, name, attrs):
		self.currElement = name
		if self.currElement == "page":
			global DOCID_CTR, DOCID_TITLE_MAP
			if DOCID_CTR%1000==0:
				if DOCID_TITLE_MAP is not None:
					DOCID_TITLE_MAP.close()
				DOCID_TITLE_MAP = open("docid_title_map-" + str(DOCID_CTR/1000), "wb")
			self.docId = str(DOCID_CTR)
			DOCID_CTR += 1
			self.title = ""
		elif self.currElement == "text":
			self.body = ""
			self.references = ""
		self.innerElement = None

	def characters(self, content):
		if self.currElement == "title":
			content = content.encode('ascii', 'ignore')
			self.title += content
		elif self.currElement == "text":
			content = content.encode('ascii', 'ignore')
			if self.innerElement is None:
				if "==External links==" in content or "== External links ==" in  content:
					self.innerElement = "externallinks"
				elif "{{Infobox" in content:
					self.innerElement = "infobox"
				elif "Category:" in content:
					content = category_re.sub(" ", content)
					content = camelcase_re.sub(r' \1', content)
					content = ignore_re.sub(" ", content)
					content = content.replace("\\", " ")
					content = content.split()
					print_content(content, "-c", self.docId)
				elif "== References ==" in content or "==References==" in content:
					self.innerElement = "references"
				elif "#REDIRECT" not in content:
					self.body += content
			elif self.innerElement == "externallinks":
				if content == "\n":
					self.newLine += 1
				else:
					self.newLine = 0
				if self.newLine == 2:
					self.newLine = 0
					self.innerElement = None
				content = url_re.sub(" ", content)
				content = camelcase_re.sub(r' \1', content)
				content = ignore_re.sub(" ", content)
				content = content.replace("\\", " ")
				content = content.split()
				print_content(content, "-e", self.docId)
			elif self.innerElement == "infobox":
				if content == "}}":
					self.innerElement = None
				elif content != "\n" and "=" in content:
					pos = content.index("=")
					content = content[pos+1:]
					content = camelcase_re.sub(r' \1', content)
					content = ignore_re.sub(" ", content)
					content = content.replace("\\", " ")
					content = content.split()
					print_content(content, "-i", self.docId)
			elif self.innerElement == "references":
				if content == "\n":
					self.newLine += 1
				else:
					self.newLine = 0
				if self.newLine == 2:
					self.newLine = 0
					self.innerElement = None
				self.references += content


	def endElement(self, name):
		if self.currElement == "text":
			content = body_re.sub(" ", self.body)
			content = url_re.sub(" ", content)
			content = camelcase_re.sub(r' \1', content)
			content = ignore_re.sub(" ", content)
			content = content.replace("\\", " ")
			content = content.split()
			print_content(content, "-b", self.docId)

			content = self.references
			content = url_re.sub(" ", content)
			content = camelcase_re.sub(r' \1', content)
			content = ignore_re.sub(" ", content)
			content = content.replace("\\", " ")
			content = content.split()
			for word in content:
				word = word.lower()
				if word not in stop_words and word not in references_ignore:
					process_word(word, "-r", self.docId)

			content = self.title
			content = camelcase_re.sub(r' \1', content)
			content = ignore_re.sub(" ", content)
			content = content.replace("\\", " ")
			content = content.split()
			print_content(content, "-t", self.docId)

			write_to_file()
			DOCID_TITLE_MAP.write(self.docId + ":" + self.title.strip() + "\n")


parser = xml.sax.make_parser()
parser.setContentHandler(WikiHandler())
parser.parse(open(sys.argv[1],"r"))

write_to_file(True)

DOCID_TITLE_MAP.close()
merge_files()

with open("docid_ctr", "wb") as f:
	f.write(str(DOCID_CTR) + "\n")
