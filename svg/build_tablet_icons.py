#!/usr/bin/python3

import json
import time
import sys
from os import listdir
from os.path import isfile, join, basename, normpath
import xml.etree.ElementTree as ET


from smartserver.svg import fileGetContents, isForbiddenTag, cleanStyles, cleanGrayscaled

		
def process_files( sourcePath, file, prefix, createGrayscaled, createCleanGrayscaled, createColored, top ):
	content = fileGetContents( sourcePath + file )
	
	name = file[0:-4]
	
	#if sourcePath.endswith('weather/'):
	#	name = 'weather_' + name
	
	symbol_count = 0;
	
	if createGrayscaled or createCleanGrayscaled:
		xml = ET.fromstring(content)
		group = ET.Element('g', attrib = { 'id': prefix + "_" + name + "_grayscaled"})
		
		cleanGrayscaled(xml, createCleanGrayscaled)

		for child in xml:
			if isForbiddenTag(child):
				continue
			#print child.tag
			group.append(child)
			
		top.append(group)
		print(" --> added default icon '" + sourcePath + group.attrib['id'] + "'")
		symbol_count = symbol_count + 1
		
	if createColored:
		xml = ET.fromstring(content)
		group = ET.Element('g', attrib = { 'id': prefix + "_" + name + "_colored"})
		for child in xml:
			if isForbiddenTag(child):
				continue
			group.append(child)
		top.append(group)
		print(" --> added colored icon '" + sourcePath + group.attrib['id'] + "'")
		symbol_count = symbol_count + 1

	return symbol_count
	
t1 = time.time()

process_count = 0
symbol_count = 0

configs = [
	{
        'name': 'openhab',
		'source': '/smartserver/data/projects/openhab_shared/svg/habpanel/openhab/',
		'grayscaled': [
			'light','settings','man_2'
		]
	},
	{
        'name': 'haus',
		'source': '/smartserver/data/projects/openhab_shared/svg/habpanel/haus/',
		'grayscaled': [
			'floor_attic','floor_first','floor_second','outside','toolshed'
		]
	},
	{
        'name': 'self',
		'source': '/smartserver/data/projects/openhab_shared/svg/habpanel/self/',
		'grayscaled': [
            'window','sensor2','info','roomba','garden','loudspeaker','energy','wind','temperature','rain','radiatore','compass_circle','compass_needle','sun'
		],
		'colored': []
	}
]
		
ET.register_namespace("","http://www.w3.org/2000/svg")
top = ET.Element('svg', attrib = { 'version':'1.1', 'xmlns:xlink':'http://www.w3.org/1999/xlink', 'x':"0px", 'y':"0px", 'viewBox':"0 0 64 64", 'enable-background':"new 0 0 64 64", 'xml:space':"preserve"})
comment = ET.Comment('Generated by Marvin')
top.append(comment)

for config in configs:
	sourcePath = config['source']
	onlyfiles = [f for f in listdir(sourcePath) if isfile(join(sourcePath, f))]

	for file in onlyfiles:
		if(file[:1] != '.' and file[-3:] == 'svg'):
			print("Processing file: " + file)
			
			prefix = config['name']#basename(normpath(sourcePath))
				
			createCleanGrayscaled = False #'clean_grayscaled' in config and file[0:-4] in config['clean_grayscaled']
			createGrayscaled = 'grayscaled' in config and file[0:-4] in config['grayscaled']
			createColored = 'colored' in config and file[0:-4] in config['colored']
			symbol_count += process_files( sourcePath, file, prefix, createGrayscaled, createCleanGrayscaled, createColored, top )
			
			process_count += 1

content = ET.tostring(top, encoding='unicode', method='xml')

f = open("../conf/html/shared/habpanel/svg/icons.svg", 'w')
f.write(content)
f.close()

t2 = time.time()
print("Done in " + str(t2-t1) + " seconds. Processed " + str(process_count) + " icons. Added " + str(symbol_count) + " icons.")

 
