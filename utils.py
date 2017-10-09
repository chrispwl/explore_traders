"""
Utility functions for
Decoding odd characters in files
Dealing for HS codes and SIC codes
"""
import pandas as pd
import sys, logging
import pkgutil
import encodings, nltk
import os
from collections import defaultdict


logging.basicConfig(filename="utils_logfile.log", level=logging.INFO)
# DEBUG, INFO, WARNING, ERROR, CRITICAL


def all_encodings():
	"""Gather all file encodings in pkgutil"""
	modnames = set(
		[modname for importer, modname, ispkg in pkgutil.walk_packages(
			path=[os.path.dirname(encodings.__file__)], prefix='')]
		)
	aliases = set(encodings.aliases.aliases.values())
	return modnames.union(aliases)


def suggest_encodings(char_error_code, char_to_find=None):
	"""
	Suggest encodings for odd characters found (typically in csv files)
	"""
	for enc in all_encodings():
		try:
			# msg = char_error_code.decode(enc)
			msg = char_error_code.decode(enc)
		except Exception:
			continue
		if (msg == char_to_find) or (char_to_find == None):
			print('Decoding {t} with {enc} is {m}'.format(
				t=char_error_code, enc=enc, m=msg))


deft_CNlist = [84118280, 84119900, 94033019, 94034090, 82121090, 84191100, 
1022949, 1061900, 3023519, 48025890, 48026115, 48026180, 48041190, 63014090, 63022290,
70131000, 70132210]

def wordcloud(CNlist=deft_CNlist, howmany=20):
	"""Returns lowercase wordcloud for commodities"""
	wcloud = defaultdict(int)
	stopwords = ['of', 'and', 'in', 'with', '.', '=', '<', '>', 'a', 'the', 'for', 'or', 
	'(', ')', ',', 'but', 'any', 'by', "''", '``', 'which', '%', 'consists']
	stopwords = stopwords + ['excl', 'total', 'n.e.s', 'other', 'purposes', 'like']
	for c in CNlist:
		desc = get_desc_by_CN(str(c))['Self-Explanatory text (English)'].values
		tokens = nltk.word_tokenize(str(desc[0]).lower())  #.split(' ')
		for tk in tokens:
			if tk not in stopwords: wcloud[tk] += 1

	wcloud = sorted(wcloud.items(), key=lambda tup: tup[1], reverse=True)
	[print(w, c) for w, c in wcloud[:howmany]]


def _make_8char_CN(trialstring):
	# Converts a Commodity Code to an 8-digit string
	# Insert leading zero for HS chapters 1 to 9:
	s = str(trialstring)
	x = len(str(trialstring)) 
	if x==7:
		outstr = '0'+s
	elif x==1:
		outstr = '0'+s
	# Insert trailing zeros for 2-digit HS chapters (anonymised)
	elif x==2:
		outstr = s+'000000'
	else:
		outstr = s
	return outstr


def _tidyup_df(df):
	# Converts all Commodity Codes in a dataframe to 8-digit strings
	outdf = df.loc[:,
		'Commodity Code'].map(lambda x: _make_8char_CN(x))
	outdf = pd.concat([outdf, df[
		['Supplementary Unit','Self-Explanatory text (English)']
		]], axis=1)
	return outdf


def _print_HS(df):
	print('\n'.join(
		[str(code)+'\t'+str(desc[:80]) for idx, code, unit, desc in 
		df.itertuples()]
		))


def get_CN_by_text(searchstring, verbose=False):
	"""
	Returns dataframe of index, CN (8-digit HS), measurement unit
	and description of commodities containing the searchstring in
	their description
	"""
	try:
		assert searchstring.isalnum()
	except:
		logging.error('invalid search string in get_CN_list()')
		return 0
	df = pd.read_csv('2017_CN.txt', sep='\t', 
		encoding='utf-16', warn_bad_lines=True)
	searchstring = str(searchstring).lower()
	if verbose: logging.info('Searching for {0}'.format(searchstring))
	foundstrings = df.loc[df.loc[:,'Self-Explanatory text (English)'
			].str.lower().str.contains(searchstring),:]
	outdf = _tidyup_df(foundstrings)  # return 8-digit string
	
	return outdf


def get_desc_by_HSchapter(chapternum, verbose=False):
	try:
		assert len(str(chapternum))<=2
	except:
		logging.error('invalid HS chapter supplied to get_desc_by_HSchapter()')
		return 0
	if len(str(chapternum))==1: chapternum = '0'+str(chapternum)
	df = pd.read_csv('2017_CN.txt', sep='\t', 
		encoding='utf-16', warn_bad_lines=True)
	foundstrings = df.loc[df.loc[:,'Commodity Code'].map(
		lambda x: _make_8char_CN(x)[:2]
		).str.match(chapternum),:]
	outdf = _tidyup_df(foundstrings)  # return 8-digit string

	return outdf


def get_desc_by_CN(df, CNcode, verbose=False):
	try:
		assert (len(str(CNcode))==8) | (len(str(CNcode))==7)
	except:
		logging.error('invalid CN code supplied to get_desc_by_CN()')
		return 0
	if len(str(CNcode))==7: CNcode = '0'+str(CNcode)
	# df = pd.read_csv('2017_CN.txt', sep='\t', 
	# 	encoding='utf-16', warn_bad_lines=True)
	# foundstrings = df.loc[df.loc[:,'Commodity Code'].map(
	# 	lambda x: _make_8char_CN(x)[:8]
	# 	).str.match(CNcode),:]
	foundstrings = df.loc[df.loc[:,'Commodity Code'].str.match(CNcode),:]
	# print(foundstrings)
	# except:
	if foundstrings.empty:
		outdf = pd.DataFrame({
			'Commodity Code': [CNcode],
			'Supplementary Unit': ['unk'],
			'Self-Explanatory text (English)': ['Code not found']
			})
		print('empty df', end=' ')
		# _print_HS(outdf)
	else:
		outdf = _tidyup_df(foundstrings)  # return 8-digit string
	# print(outdf)

	return outdf


def update_progress_bar(progress, time_elapsed, prefix="", suffix=""): # remcount
    """progress from zero+ to one"""
    togo = time_elapsed*(1-progress)/progress/60
    if togo > 240:
        print("\rProgress: [{0:.<20s}] {1:.2f}%, {2:,}s elapsed, ~{3:,} hrs to go{4}".format(
                '#'*int(progress*20), progress*100, int(time_elapsed), int(togo/60), 
                str(suffix)
            ), end='')
    else:
        print("\rProgress: [{0:.<20s}] {1:.2f}%, {2:,}s elapsed, ~{3:,} mins to go{4}".format(
                '#'*int(progress*20), progress*100, int(time_elapsed), togo, str(suffix)
            ), end='')


