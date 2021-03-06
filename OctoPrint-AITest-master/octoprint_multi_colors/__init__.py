# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.events
from octoprint.events import Events
from octoprint.server import printer
from octoprint.filemanager import FileDestinations

import logging

from flask import jsonify
import os.path
from os import linesep
import datetime
import mmap
import re
import contextlib
from shutil import copyfile
import os

class MultiColorsPlugin(octoprint.plugin.AssetPlugin,
					octoprint.plugin.SimpleApiPlugin,
					octoprint.plugin.TemplatePlugin,
					octoprint.plugin.SettingsPlugin):

	def initialize(self):
		#self._logger.setLevel(logging.DEBUG)
		self.gcode_file = os.path.join(self.get_plugin_data_folder(),"gcode.txt")
		self.regex_file = os.path.join(self.get_plugin_data_folder(),"regex.txt")
		self._logger.info("MultiColors init")
		

	def get_template_configs(self):
		return [
			dict(type="tab", template="multi_colors_tab.jinja2", custom_bindings=True)
		]

	def get_assets(self):
		return dict(
			js=["js/multi_colors.js"]
		)

	def is_api_adminonly(self):
		return True

	def get_api_commands(self):
		return dict(
			settings=[],
                         
			process=["file", "gcode", "layers", "find_string"],
                        
		)

	def rename(self, fname):
		name, ext = os.path.splitext(fname)
		if name.endswith("_multi"):
			return fname
		else:
			return "%s_multi%s"%(name, ext)

        
	def on_api_command(self, command, data):
		self._logger.info("on_api_command called: '{command}' / '{data}'".format(**locals()))
		if command == "settings":
				return jsonify(dict(gcode =  self.load_gcode(), find_string =  self.load_regex()))
		elif command == "process":
			self.save_gcode(data.get('gcode'))
			self.save_regex(data.get('find_string'))
			
			#selected file
			gcode_file = os.path.join(self._settings.global_get_basefolder('uploads'), data.get('file') )
			
			#create temp file
			work_copy = "%s.tmp"%gcode_file
			copyfile(gcode_file, work_copy)

			#code injection
			
			ret, message = self.inject_gcode(work_copy, data.get('layers').replace(",", " ").split(), data.get('find_string'), data.get('gcode'))
			
			
			if ret != "error": 
				if data.get('duplicate'):
					gcode_file = os.path.join(self._settings.global_get_basefolder('uploads'), self.rename(data.get('file')) )
				
				#copy temp file 
				copyfile(work_copy, gcode_file)
				
				#start file analysis
				self._file_manager.analyse(FileDestinations.LOCAL, gcode_file) 
				
			#cleanup
			os.remove( work_copy )
				
			return jsonify(dict(status=ret, message=message))

	def inject_gcode(self, file, layers, find_string, gcode):
		try:
			self._logger.info("File to modify '%s'"%file)
			
			marker = "; changing speed"
			line_found = False
			with open(file, "r") as f:
			    line_found = any(marker in line for line in f)

			found = 0
			
			replace  = ur'\1{2}{0}{2}{1}{2}'.format(marker, gcode, linesep)
				
			for layer in layers:
				with open(file, 'r+') as f:
					self._logger.info("Trying to insert printing speed code for layer '%s'..."%layer)
					search = re.compile(ur'({0}(\r\n?|\n))'.format( find_string.format(layer = int(layer))) , re.MULTILINE)
					self._logger.debug(search.pattern)
					with contextlib.closing(mmap.mmap(f.fileno(), 0)) as m:
						test = re.search(search, m)
						if test:
							found += 1
							result = re.sub(search, replace, m)
							f.seek(0)
							f.write(result)
							f.flush()
						else:
							self._logger.info("Failed to insert code for layer %s"%layer)

			needed = len(layers)
			if needed == found:
				if line_found: 
					return "info", "ATTENTION!!! This file has been processed before!!!. You might overwrite the previous setting. %s GCODE injected successfuly."%found
				else:
					return "success", "%s GCODE injected successfuly."%found
			else:
				return "error", "Injecting GCODE failed. Replaced %s out of %s needed."%(found, needed)
		except Exception as e:
			self._logger.error(e)
			return "error", "Injecting GCODE failed [%s]"%e

	def load_regex(self):
		data = self._load_data(self.regex_file)
		if data == "__default__":
			return "layer {layer},.*?" 
		return data
		
	def save_regex(self, data):
		self._save_data(self.regex_file, data)
		
	def load_gcode(self):
		data = self._load_data(self.gcode_file)
		if data == "__default__":
			return """M220 Change printing speed"""
		return data
		
	def save_gcode(self, data):
		self._save_data(self.gcode_file, data)
		
	def _load_data(self, data_file):
		data = "__default__"
		if os.path.isfile(data_file):
			with open(data_file, 'r') as f:
				data = f.read()
		return data
		
	def _save_data(self, data_file, data):
		with open(data_file, 'w') as f:
			f.write(data)

	def get_version(self):
		return self._plugin_version

	def get_update_information(self):
		return dict(
			multi_colors=dict(
				displayName="Multi Colors",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="MoonshineSG",
				repo="OctoPrint-MultiColors",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/MoonshineSG/OctoPrint-MultiColors/archive/{target_version}.zip"
			)
		)

__plugin_name__ = "AI Test"
__plugin_description__ = "Inject GCODE at specified layers to accomendate the environment."

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = MultiColorsPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
