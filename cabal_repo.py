#!/usr/bin/env python
from __future__ import print_function
import tarfile
import os
import sys

class RepoError(RuntimeError): pass

NAME = 'name'
VERSION = 'version'

def tarjoin(*a):
	# tarfiles have "/" path separators, even on windows.
	return "/".join(a)

class Package(object):
	def __init__(self, name, version, path, cabal_path):
		self.name = name
		self.version = version
		self.path = path
		self.cabal_path = cabal_path
		self.cabal_filename = os.path.basename(cabal_path)
	
	@property
	def cabal_index_path(self):
		return tarjoin(self.name, self.version, self.cabal_filename)

	@property
	def archive_path(self):
		return os.path.join(self.name, self.version, self.package_id + ".tar.gz")

	@property
	def package_id(self):
		return "%s-%s" % (self.name, self.version)

	def __str__(self):
		return "%s (%s)" % (self.name, self.version)

def create_local_repo(repo_path, src_paths):
	print("Creating cabal package repo in %s" % (os.path.abspath(repo_path),))
	os.makedirs(repo_path)
	packages = {}
	seen_paths = set()

	for path in src_paths:
		if not path.strip():
			# skip empty path
			continue

		if path in seen_paths:
			# skip duplicate locations
			continue

		seen_paths.add(path)
		cabal_file = find_cabal_file(path)
		info = cabal_info(cabal_file)
		name = info[NAME]
		version = info[VERSION]
		package = Package(
				name=name,
				version=version,
				path=path,
				cabal_path=cabal_file)

		if package.name in packages:
			print("Package already added - skipping %r\n (from %s)"
				% (package, path))
			continue

		packages[name] = package
	
	zip_packages(repo_path, packages.values())

def find_cabal_file(path):
	contents = os.listdir(path)
	is_cabal_file = lambda x: x.endswith('.cabal') and os.path.isfile(os.path.join(path, x))
	cabal_files = list(filter(is_cabal_file, contents))
	num_files = len(cabal_files)
	if num_files == 1:
		return os.path.join(path, cabal_files[0])
	else:
		raise RepoError(
			"Unexpected number of .cabal files in %s (%s)" %
			(path, num_files))

def cabal_info(cabal_file_path):
	data = {}
	KEYS = set([NAME, VERSION])
	sep = ":"
	with open(cabal_file_path) as cabal_file:
		for line in cabal_file:
			try:
				key, val = line.split(sep, 1)
			except ValueError:
				pass
			else:
				key = key.strip().lower()
				val = val.strip()
				if key in KEYS:
					data[key] = val
	if set(data.keys()) != KEYS:
		raise RepoError(
			"Couldn't get all required info from cabal file\n - got: %r"
			% (data,))
	return data

def zip_packages(base, packages):
	MODE = 'w:gz'
	with tarfile.open(os.path.join(base, '00-index.tar'), 'w') as index:
		for package in packages:
			index.add(package.cabal_path, arcname=package.cabal_index_path)
			archive_base = os.path.dirname(package.archive_path)
			os.makedirs(os.path.join(base, archive_base))
			with tarfile.open(os.path.join(base, package.archive_path), MODE) as archive:
				archive.add(package.path, arcname = package.package_id)
			print("Added source package: %s" % (package,))

if __name__ == '__main__':
	import optparse
	p = optparse.OptionParser('usage: %prog [OPTIONS] repo_path')
	opts, args = p.parse_args()
	assert len(args) == 1, p.format_help()

	repo_path, = args
	sources = set(os.environ['CABAL_PKG_PATH'].split(os.pathsep))
	create_local_repo(repo_path, sources)


