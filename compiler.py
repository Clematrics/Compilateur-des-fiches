# coding: utf-8
import re
import json
import importlib
macros = importlib.import_module('macros')

"""
bindings est consruit commme un dictionnaire où à chaque tag spécifique est associé un 
chemin dans le drive, relatif à "_PREPA", pointant sur le fichier concerné
"""
bindings = None
"""
layouts est construit comme un dictionnaire {types de cartes: liste des attributs} 
"""
layouts = None
"""
les cartes sont regroupés par type
"""
cards = {}
header = ''

### BINDINGS GENERATION ###

def flatten(arg):
	flat_dict = dict( [key, arg[key] for key in arg if arg[key] is str] ) # pas besoin de tesster les collisions entre str, ils sont évités par le standard json
	for key in [k for k in arg if arg[k] is dict]:
		res = flatten(arg[key])
		for k in res:
			if k in flat_dict:
				print(f'ERROR : "{key}":"{flat_dict[key]}" already exists and cannot be replaced by "{key}":"{arg[key]}"')
			else:
				flat_dict[k] = key + '/' + res[k]
	return flat_dict


def generate_bindings(obj):
	"""
	En entrée, on a un dictionnaire décrivant l'arborescence des fichiers avec pour éléments :
		soit un nom: dictionnaire, ou nom est le nom du sous-dossier, et le dictionnaire décrit l'arborescence de ce dernier
		soit un nom: string, ou nom est le nom du tag et string le nom du fichier associé
	on aplati ici cette arborescence en préfixant chaque fichier des noms des dossiers parents
	on obtient donc un dictionnaire nom: string, ou string est le chemin d'accès au fichier associé au tag nom 
	"""
	bindings = flatten(obj)


### HEADER GENERATION ###

def generate_header():
	#TODO placer le fichier du package cardsheader dans le dossier de MikTeX
	# (ou trouver un moyen de l'ajouter) ou de le placer dans un des répertoires d'Anki

	return (r'\documentclass[12pt]{article}' + '\n'
			r'\special{papersize=3in,5in}' + '\n'
			r'\usepackage{cardsheader}' + '\n'
			r'\pagestyle{empty}' + '\n'
			r'\setlength{\parindent}{0in}' + '\n'
			r'\begin{document}'
	)

### CARDS GENERATION ###

pos = 0
todos = 0
cards_nb = 0
current_card = {}
current_type = ''
ignore_card = False
current_field = [] # field représenté par liste de lignes
tags = []
tags_stat = {}
add_specific_tags = []
del_specific_tags = []
metadata = {}


def print_error(arg):
	print(f'ERROR ! Line {pos + 1} : {arg}'))

def preprocess():
	pos = 0
	
	for line in raw_cards:
		while start = line.find('%%') != -1:
			end = line.find('%%', start + 2)
			if end == -1:
				print_error('A macro is not delimited.')
				raise Exception('')
			macro = strip( line[start + 2:end] )
			macro = re.split(r'\s*', macro)

			try:
				line[start + 2:end] = getattr( macros, macro[0] )(macro[1:])
			except:
				print_error(f'The macro {macro[0]} is not defined.')
				del line[start + 2:end]
		pos += 1
	
	return True

def transition_start_import(line):
	if re.match(r'\s*%%% START_ANKI_IMPORT %%%', line):
		return True
	return False

def transition_end_import(line):
	if re.match(r'\s*%%% END_ANKI_IMPORT %%%', line):
		return True
	return False

def transition_tag(line):
	m = re.match(r'\s*%(>)?(?(1)(?P<specific>>?)|<(?P<specific><?))\s*(?P<tag>(\w|:)+)', line)
	if m and m.group(1) == '>':
		if m.group('specific') == '>':
			add_specific_tags.append(m.group('tag'))
		else:
			tags.append(m.group('tag'))
		return True
	elif m and m.group(1) == '':
		if m.group('specific') == '<':
			del_specific_tags.append(m.group('tag'))
		else:
			tags = [x for x in tags if x != m.group('tag')]
		return True
	return False

def transition_metadata(line):
	m = re.match(r'\s*%!(>)?(?(1)|<) (?P<id>\w+) (?(1)(?P<metadata>.*)$|)', line):
	if m and m.group(1) == '>':
		metadata[m.group('id')] = m.group('metadata')
		return True
	elif m:
		if m.group('id') in metadata:
			del metadata[m.group('id')]
		else:
			print_error(f'The metadata\'s id {m.group('id')} is not defined (anymore ?) !')
		return True
	return False

def transition_todo(line):
	if re.match(r'\s*%\s*[tT][oO][dD][oO]', line):
		todos += 1
		return True
	return False

def transition_begin(line):
	if re.match(r'\s*\begin\{fiche\}', line):
		current_card = {}
		current_type = ''
		ignore_card = False
		current_field = []
		return True
	return False

def transition_end(line):
	if re.match(r'\s*\end\{fiche\}', line):
		if not ignore_card:
			cards_nb += 1
			current_card['tags'] = ' '.join(tags + specific_tags)
			for tag in list( set(tags).union(add_specific_tags).difference(del_specific_tags) ): # gestion des statistiques
				l = tag.split(':')
				for real_tag in [l[:i] for i in range(len(l))]:
					tags_stat.get(real_tag, 0) += 1
			cards.get(current_type, []).append(current_card)
		add_specific_tags = []
		del_specific_tags = []
		return True
	return False
	
def transition_type(line):
	m = re.match(r'\s*%t\s*(?P<type_name>\w+)', line):
	if m:
		type_name = m.group['type_name']
		if type_name not in layouts.keys():
			print_error(f'{type_name} is not a type of card described in the layouts descriptor file ! Ignoring this card')
			ignore_card = True
		current_type = type_name
		return True
	return False

def transition_field(line):
	m = re.match(r'\s*/- (?P<field_name>(\w| )+)-*/ (?P<content>.*)', line):
	if m:
		field_name = m.group['field_name']
		content = m.group['content']
		current_field = field_name
		current_card.get(current_field, []).append(content)
		return True
	return False

def transition_field_ext(line):
	m = re.match(r'\s*/- -+/ (?P<content>.*)', line): # TODO question : content inclut-t-il la fin de ligne \n ?
	if m:
		content = m.group['content']
		current_card.get(current_field, []).append(content)
		return True
	return False

def transition_comment(line):
	if re.match(r'\s*%-', line):
		return True
	return False

def transition_empty(line):
	if re.fullmatch(r'\s*$', line):
		return True
	return False

def automata():
	pos = 0
	end = len(raw_cards)
	state = 0
	importing = False

	while pos != end:
		line = line[pos]

		if state == 0:
			if transition_start_import(line):
				importing = True
				state = 1
		elif state == 1:
			if transition_end_import(line):
				print('\n--- Import successful ! ---\n')
				importing = False
			elif transition_todo(line):
				print(f'Warning line {pos + 1} : TODO remaining')
			elif transition_tag(line)
			or transition_metadata(line)
			or transition_comment(line)
			or transition_empty(line):
				pass
			elif transition_begin(line):
				state = 2
			else:
				print_error(f'state {state}')
				raise Exception('')
		elif state == 2:
			if transition_type(line):
				state = 3
			elif transition_comment(line)
			or transition_empty(line):
				pass
			else:
				print_error(f'state {state}')
				raise Exception('')
		elif state == 3:
			if transition_field(line)
			or transition_field_ext(line)
			or transition_comment(line)
			or transition_empty(line):
				pass
			elif transition_end(line):
				state = 1
			else:
				print_error(f'state {state}')
				raise Exception('')

		pos += 1

	if importing:
		print('Warning : end file reached while importing. Writing files anyway.')

def reformat(line):
	return line.replace('"', '""').replace('<', '&lt;').replace('>', '&gt;')

def field_index(field, card_type):
	if field == 'tags':
		return len(layouts[card_type])
	try:
		return layouts[card_type].index(field)
	except ValueError:
		print_error(f'The field {field} is not included in the {card_type}\'s layout')

def write_cards():
	for card_type in cards.keys():
		with open(f'compiled/{card_type}.txt', 'w') as stream:
			for card in cards[card_type]:
				card_fields = []
				for field in card.keys():
					field_string = f'"{'&lt;br&gt;'.join( [reformat(line) for line in field] )}"'
					card_fields[field_index(field, card_type)] = field_string
				card_string = ';'.join(card_fields)
				stream.write(card_string)

def compile_cards():
	preprocess()
	automata()
	write_cards()
	print('\n--- Import complete ! ---\n')
	print(f'Todos left : {todos}')
	for card_type in cards.keys():
		print(f'Il y a {len( cards[card_type] )} cartes du type {card_type}')
	for tag in tags_stat.keys():
		print(f'{len( tags_stat[tag] )} cartes générées avec le tag {tag}')

def main():
	with open('bindings.json', 'r') as stream:
		generate_bindings( json.loads( stream.read() ) )

	with open('layouts.json', 'r') as stream:
		layouts = json.loads( stream.read() )
	
	macros.init(bindings, layouts)

	with open('fiches.tex', 'r') as stream:
		raw_cards = list(stream)
	try:
		compile_cards()
	except:
		print('\n--- FATAL ERROR. ABORT ! lol ---\n')

	generate_header()

main()
pause = input('pause')





















