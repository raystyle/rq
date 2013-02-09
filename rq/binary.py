#!/usr/bin/env python
"""
This program extracts data from RPM and SRPM packages and stores it in
a database for later querying.

based on the srpm script of similar function copyright (c) 2005 Stew Benedict <sbenedict@mandriva.com>
copyright (c) 2007-2011 Vincent Danen <vdanen@linsec.ca>

This file is part of rq.

rq is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

rq is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with rq.  If not, see <http://www.gnu.org/licenses/>.
"""
import os, sys, re, commands, logging, tempfile, shutil, datetime
from glob import glob
import rq.db
import rq.basics

class Binary:
    """
    Class to handle working with source files
    """

    def __init__(self, db, config, options, rtag, rcommon):
        self.db      = db
        self.config  = config
        self.options = options
        self.rtag    = rtag
        self.rcommon = rcommon

        self.re_brpm     = re.compile(r'\.rpm$')
        self.re_srpm     = re.compile(r'\.src\.rpm$')
        self.re_patch    = re.compile(r'\.(diff|dif|patch)(\.bz2|\.gz)?$')
        self.re_tar      = re.compile(r'\.((tar)(\.bz2|\.gz)?|t(gz|bz2?))$')
        self.re_targz    = re.compile(r'\.(tgz|tar\.gz)$')
        self.re_tarbz    = re.compile(r'\.(tbz2?|tar\.bz2)$')
        self.re_patchgz  = re.compile(r'\.(patch|diff|dif)(\.gz)$')
        self.re_patchbz  = re.compile(r'\.(patch|diff|dif)(\.bz2)$')
        self.re_srpmname = re.compile(r'(\w+)(-[0-9]).*')

        self.excluded_symbols = ['abort', '__assert_fail', 'bindtextdomain', '__bss_start', 'calloc',
                                 'chmod', 'close', 'close_stdout', '__data_start', 'dcgettext', 'dirname',
                                 '_edata', '_end', 'error', '_exit', 'exit', 'fclose', 'fdopen', 'ferror',
                                 'fgets', '_fini', 'fnmatch', 'fopen', 'fork', 'fprintf', '__fprintf_chk',
                                 'fread', 'free', 'fscanf', 'fwrite', 'getenv', 'getgrgid', 'getgrnam',
                                 'getopt', 'getopt_long', 'getpwnam', 'getpwuid', 'gettimeofday',
                                 '__gmon_start__', '_init', 'ioctl', '_IO_stdin_used', 'isatty', 'iswalnum',
                                 'iswprint', 'iswspace', '_Jv_RegisterClasses', 'kill', '__libc_csu_fini',
                                 '__libc_csu_init', '__libc_start_main', 'localtime', 'malloc', 'memchr',
                                 'memcpy', '__memcpy_chk', 'memmove', 'mempcpy', '__mempcpy_chk', 'memset',
                                 'mkstemp', 'mktime', 'opendir', 'optarg', 'pclose', 'pipe', 'popen',
                                 '__printf_chk', '__progname', '__progname_full', 'program_invocation_name',
                                 'program_invocation_short_name', 'program_name', 'read', 'readdir',
                                 'readlink', 'realloc', 'rename', 'setenv', 'setlocale', 'sigaction',
                                 'sigaddset', 'sigemptyset', 'sigismember', 'signal', 'sigprocmask',
                                 '__stack_chk_fail', 'stderr', 'stdout', 'stpcpy', 'strcasecmp', 'strchr',
                                 'strcmp', 'strcpy', 'strerror', 'strftime', 'strlen', 'strncasecmp',
                                 'strnlen', 'strrchr', 'strstr', 'strtol', 'textdomain', 'time', 'umask',
                                 'unlink', 'Version', 'version_etc_copyright', 'waitpid', 'write', '__xstat']

        # caches
        self.symbol_cache   = {}
        self.provides_cache = {}
        self.requires_cache = {}
        self.group_cache    = {}
        self.user_cache     = {}


    def rpm_add_directory(self, tag, path, updatepath):
        """
        Function to import a directory full of RPMs
        """
        logging.debug('in Binary.rpm_add_directory(%s, %s, %s)' % (tag, path, updatepath))

        if not os.path.isdir(path):
            print 'Path (%s) is not a valid directory!' % path
            sys.exit(1)

        if not os.path.isdir(updatepath):
            print 'Path (%s) is not a valid directory!' % updatepath
            sys.exit(1)

        file_list = []
        file_list.extend(glob(path + "/*.rpm"))

        if len(file_list) == 0:
            print 'No files found in %s, checking subdirectories...' % path
            # newer versions of Fedora have packages in subdirectories
            subdirs = [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
            for s in subdirs:
                npath = '%s/%s' % (path, s)
                file_list.extend(glob(npath + "/*.rpm"))

        if len(file_list) == 0:
            print 'No files found to import in directory: %s' % path
            sys.exit(1)

        file_list.sort()

        tag_id = self.rtag.add_record(tag, path, updatepath)
        if tag_id == 0:
            logging.critical('Unable to add tag "%s" to the database!' % tag)
            sys.exit(1)

        for file in file_list:
            if not os.path.isfile(file):
                print 'File %s not found!\n' % file
            elif not self.re_brpm.search(file):
                print 'File %s is not a binary rpm!\n' % file
            else:
                self.record_add(tag_id, file)


    def record_add(self, tag_id, file, update=0):
        """
        Function to add a record to the database
        """
        logging.debug('in Binary.record_add(%s, %s, %d)' % (tag_id, file, update))

        if os.path.isfile(file):
            path = os.path.abspath(os.path.dirname(file))
        else:
            path = os.path.abspath(file)
        logging.debug('Path:\t%s' % path)

        self.rcommon.file_rpm_check(file)

        record = self.package_add_record(tag_id, file, update)
        if not record:
            return

        file_list = self.rcommon.rpm_list(file)
        if not file_list:
            return

        logging.debug('Add file records for package record: %s' % record)
        self.add_records(tag_id, record, file_list)
        self.add_requires(tag_id, record, file)
        self.add_provides(tag_id, record, file)
        self.add_binary_records(tag_id, record, file)

        if self.options.progress:
            sys.stdout.write('\n')


    def package_add_record(self, tag_id, file, update=0):
        """
        Function to add a package record
        """
        logging.debug('in Binary.package_add_record(%s, %s, %d)' % (tag_id, file, update))

        fname   = os.path.basename(file)
        rpmtags = commands.getoutput("rpm -qp --nosignature --qf '%{NAME}|%{VERSION}|%{RELEASE}|%{BUILDTIME}|%{ARCH}|%{SOURCERPM}' " + self.rcommon.clean_shell(file))
        tlist   = rpmtags.split('|')
        logging.debug("tlist is %s " % tlist)
        package = tlist[0].strip()
        version = tlist[1].strip()
        release = tlist[2].strip()
        pdate   = tlist[3].strip()
        arch    = tlist[4].strip()
        srpm    = self.re_srpmname.sub(r'\1', tlist[5].strip())

        query = "SELECT tag FROM tags WHERE t_record = '%s' LIMIT 1" % tag_id
        tag   = self.db.fetch_one(query)

        query = "SELECT t_record, p_package, p_version, p_release, p_arch FROM packages WHERE t_record = '%s' AND p_package = '%s' AND p_version = '%s' AND p_release = '%s' AND p_arch = '%s'" % (
            tag_id,
            self.db.sanitize_string(package),
            self.db.sanitize_string(version),
            self.db.sanitize_string(release),
            self.db.sanitize_string(arch))
        result = self.db.fetch_all(query)

        if result:
            print 'File %s-%s-%s.%s is already in the database under tag %s' % (package, version, release, arch, tag)
            return(0)

        ## TODO: we shouldn't have to have p_tag here as t_record has the same info, but it
        ## sure makes it easier to sort alphabetically and I'm too lazy for the JOINs right now

        query  = "INSERT INTO packages (t_record, p_tag, p_package, p_version, p_release, p_date, p_arch, p_srpm, p_fullname, p_update) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', %d)" % (
            tag_id,
            self.db.sanitize_string(tag),
            self.db.sanitize_string(package),
            self.db.sanitize_string(version),
            self.db.sanitize_string(release),
            self.db.sanitize_string(pdate),
            self.db.sanitize_string(arch),
            self.db.sanitize_string(srpm),
            self.db.sanitize_string(fname),
            update)

        result = self.db.do_query(query)
        self.rcommon.show_progress(fname)

        query    = "SELECT p_record FROM packages WHERE t_record = '%s' AND p_package = '%s' ORDER BY p_record DESC" % (tag_id, self.db.sanitize_string(package))
        p_record = self.db.fetch_one(query)
        if p_record:
            return(p_record)
        else:
            print 'Adding file %s failed!\n' % file
            return(0)


    def query(self, type):
        """
        Function to run the query for binary RPMs

        Valid types are: files, provides, requires, symbols, packages
        """
        logging.debug('in Binary.query(%s)' % type)

        tag_id = self.rtag.lookup(self.options.tag)
        if self.options.tag and not tag_id:
            print 'Tag %s is not a known tag!\n' % self.options.tag
            sys.exit(1)
        elif self.options.tag and tag_id:
            tag_id =  tag_id['id']

        if self.options.ignorecase and not self.options.regexp:
            ignorecase = ''
        else:
            ignorecase = 'BINARY'

        if type == 'files':
            like_q = self.options.query
        if type == 'provides':
            like_q = self.options.provides
        if type == 'requires':
            like_q = self.options.requires
        if type == 'symbols':
            like_q = self.options.symbols
        if type == 'packages':
            like_q = self.options.query

        if self.options.regexp:
            match_type = 'regexp'
        else:
            match_type = 'substring'

        if not self.options.quiet:
            print 'Searching database records for %s match for %s (%s)' % (match_type, type, like_q)

        if type == 'files':
            query = "SELECT DISTINCT p_tag, p_update, p_package, p_version, p_release, p_date, p_srpm, files, f_id, f_user, f_group, f_is_suid, f_is_sgid, f_perms FROM files LEFT JOIN packages ON (packages.p_record = files.p_record) LEFT JOIN user_names ON (files.u_record = user_names.u_record) LEFT JOIN group_names ON (files.g_record = group_names.g_record) WHERE %s files " % ignorecase
        elif type == 'symbols':
            query = "SELECT DISTINCT p_tag, p_update, p_package, p_version, p_release, p_date, p_srpm, s_name, symbols.f_id, files FROM symbols LEFT JOIN (packages, files) ON (packages.p_record = symbols.p_record AND symbols.f_id = files.f_id) JOIN symbol_names ON (symbol_names.s_record = symbols.s_record) WHERE %s s_name " % ignorecase
        elif type == 'packages':
            query = "SELECT DISTINCT p_tag, p_update, p_package, p_version, p_release, p_date, p_srpm FROM packages WHERE %s p_package " % ignorecase
        elif type == 'provides':
            query = "SELECT DISTINCT p_tag, p_update, p_package, p_version, p_release, p_date, p_srpm, pv_name FROM provides LEFT JOIN packages ON (packages.p_record = provides.p_record) JOIN provides_names ON (provides_names.pv_record = provides.pv_record) WHERE %s pv_name " % ignorecase
        elif type == 'requires':
            query = "SELECT DISTINCT p_tag, p_update, p_package, p_version, p_release, p_date, p_srpm, rq_name FROM requires LEFT JOIN packages ON (packages.p_record = requires.p_record) JOIN requires_names ON (requires_names.rq_record = requires.rq_record) WHERE %s rq_name " % ignorecase

        if self.options.regexp:
            query = query + "RLIKE '" + self.db.sanitize_string(like_q) + "'"
        else:
            query = query + "LIKE '%" + self.db.sanitize_string(like_q) + "%'"

        if self.options.tag:
            query = "%s AND %s.t_record = '%d'"  % (query, type, tag_id)

        if type == 'packages':
            query  = query + " ORDER BY p_tag, p_package"
        elif type == 'symbols':
            query = query + " ORDER BY s_name"
        elif type == 'provides':
            query = query + " ORDER BY pv_name"
        elif type == 'requires':
            query = query + " ORDER BY rq_name"
        else:
            query  = query + " ORDER BY p_tag, p_package, " + type

        result = self.db.fetch_all(query)
        if result:
            if self.options.count:
                if self.options.quiet:
                    print len(result)
                else:
                    if self.options.tag:
                        print '%d match(es) in database for tag (%s) and %s (%s)' % (len(result), self.options.tag, match_type, like_q)
                    else:
                        print '%d match(es) in database for %s (%s)' % (len(result), match_type, like_q)
                return

            ltag = ''
            lsrc = ''
            for row in result:
                utype = ''
                # for readability
                fromdb_tag  = row['p_tag']
                fromdb_rpm  = row['p_package']
                fromdb_ver  = row['p_version']
                fromdb_rel  = row['p_release']
                fromdb_date = row['p_date']
                fromdb_srpm = row['p_srpm']

                if type == 'provides':
                    fromdb_type = row['pv_name']

                if type == 'requires':
                    fromdb_type = row['rq_name']

                if type == 'files':
                    # only provides, requires, files
                    fromdb_type = row['files']

                if type == 'files':
                    fromdb_user    = row['f_user']
                    fromdb_group   = row['f_group']
                    fromdb_is_suid = row['f_is_suid']
                    fromdb_is_sgid = row['f_is_sgid']
                    fromdb_perms   = row['f_perms']
                    fromdb_fileid  = row['f_id']

                if type == 'symbols':
                    fromdb_files   = row['files']
                    fromdb_s_name  = row['s_name']

                if row['p_update'] == 1:
                    utype = '[update] '

                if not ltag == fromdb_tag:
                    if not type == 'packages':
                        print '\n\nResults in Tag: %s\n%s\n' % (fromdb_tag, '='*40)
                    ltag = fromdb_tag

                if self.options.debug:
                    print row
                else:
                    rpm = '%s-%s-%s' % (fromdb_rpm, fromdb_ver, fromdb_rel)

                    if not rpm == lsrc:
                        if type == 'files' and self.options.ownership:
                            is_suid = ''
                            is_sgid = ''
                            if fromdb_is_suid == 1:
                                is_suid = '*'
                            if fromdb_is_sgid == 1:
                                is_sgid = '*'
                            print '%s (%s): %s (%04d,%s%s,%s%s)' % (rpm, fromdb_srpm, fromdb_type, int(fromdb_perms), is_suid, fromdb_user, is_sgid, fromdb_group)
                        elif type == 'symbols':
                            print '%s (%s): %s in %s' % (rpm, fromdb_srpm, fromdb_s_name, fromdb_files)
                        elif type == 'packages':
                            print '%s/%s %s' % (ltag, rpm, utype)
                        else:
                            print '%s%s (%s): %s' % (utype, rpm, fromdb_srpm, fromdb_type)

                    if self.options.quiet:
                        lsrc = rpm
                    else:
                        flag_result = None
                        if self.options.extrainfo:
                            if type == 'files':
                                query       = 'SELECT * FROM flags WHERE f_id = %d LIMIT 1' % fromdb_fileid
                                flag_result = self.db.fetch_all(query)
                                if flag_result:
                                    for x in flag_result:
                                        #fetch_all returns a tuple containing a dict, so...
                                        flags = self.convert_flags(x)
                            rpm_date = datetime.datetime.fromtimestamp(float(fromdb_date))
                            if flag_result:
                                print '  %-10s%s' % ("Date :", rpm_date.strftime('%a %b %d %H:%M:%S %Y'))
                                print '  %-10s%-10s%-12s%-10s%-12s%-10s%s' % ("Flags:", "RELRO  :", flags['relro'], "SSP:", flags['ssp'], "PIE:", flags['pie'])
                                print '  %-10s%-10s%-12s%-10s%s' % ("", "FORTIFY:", flags['fortify'], "NX :", flags['nx'])

        else:
            if self.options.tag:
                print 'No matches in database for tag (%s) and %s (%s)' % (self.options.tag, match_type, like_q)
            else:
                print 'No matches in database for %s (%s)' % (match_type, like_q)


    def cache_get_user(self, name):
        """
        Function to look up the u_record and add it to the cache for users
        """
        query = "SELECT u_record FROM user_names WHERE f_user = '%s'" % name
        u_rec = self.db.fetch_one(query)
        if u_rec:
            # add to the cache
            self.user_cache[name] = u_rec
            return u_rec
        else:
            return False


    def get_user_record(self, user):
        """
        Function to lookup, add, and cache user info
        """
        name = self.db.sanitize_string(user)

        # first check the cache
        if name in self.user_cache:
            return self.user_cache[name]

        # not cached, check the database
        u_rec = self.cache_get_user(name)
        if u_rec:
            return u_rec

        # not cached, not in the db, add it
        query = "INSERT INTO user_names (u_record, f_user) VALUES (NULL, '%s')" % name
        u_rec = self.db.do_query(query, True)
        if u_rec:
            # add to the cache
            self.user_cache[name] = u_rec
            return u_rec


    def cache_get_group(self, name):
        """
        Function to look up the g_record and add it to the cache for groups
        """
        query = "SELECT g_record FROM group_names WHERE f_group = '%s'" % name
        g_rec = self.db.fetch_one(query)
        if g_rec:
            # add to the cache
            self.group_cache[name] = g_rec
            return g_rec
        else:
            return False


    def get_group_record(self, group):
        """
        Function to lookup, add, and cache group info
        """
        name = self.db.sanitize_string(group)

        # first check the cache
        if name in self.group_cache:
            return self.group_cache[name]

        # not cached, check the database
        g_rec = self.cache_get_group(name)
        if g_rec:
            return g_rec

        # not cached, not in the db, add it
        query = "INSERT INTO group_names (g_record, f_group) VALUES (NULL, '%s')" % name
        g_rec = self.db.do_query(query, True)
        if g_rec:
            # add to the cache
            self.group_cache[name] = g_rec
            return g_rec


    def cache_get_requires(self, name):
        """
        Function to look up the rq_record and add it to the cache for requires
        """
        query = "SELECT rq_record FROM requires_names WHERE rq_name = '%s'" % name
        rq_rec = self.db.fetch_one(query)
        if rq_rec:
            # add to the cache
            self.requires_cache[name] = rq_rec
            return rq_rec
        else:
            return False


    def get_requires_record(self, requires):
        """
        Function to lookup, add, and cache requires info
        """
        name = self.db.sanitize_string(requires)

        # first check the cache
        if name in self.requires_cache:
            return self.requires_cache[name]

        # not cached, check the database
        rq_rec = self.cache_get_requires(name)
        if rq_rec:
            return rq_rec

        # not cached, not in the db, add it
        query  = "INSERT INTO requires_names (rq_record, rq_name) VALUES (NULL, '%s')" % name
        rq_rec = self.db.do_query(query, True)
        if rq_rec:
            # add to the cache
            self.requires_cache[name] = rq_rec
            return rq_rec


    def add_requires(self, tag_id, record, file):
        """
        Function to add requires to the database
        """
        logging.debug('in Binary.add_requires(%s, %s, %s)' % (tag_id, record, file))

        list = commands.getoutput("rpm -qp --nosignature --requires " + self.rcommon.clean_shell(file) + " | egrep -v '(rpmlib|GLIBC|GCC|rtld)' | uniq")
        list = list.splitlines()
        for dep in list:
            if dep:
                self.rcommon.show_progress()
                if self.options.verbose:
                    print 'Dependency: %s' % dep
                rq_rec = self.get_requires_record(dep.strip())
                query  = "INSERT INTO requires (t_record, p_record, rq_record) VALUES ('%s', '%s', '%s')" % (tag_id, record, rq_rec)
                result = self.db.do_query(query)


    def cache_get_provides(self, name):
        """
        Function to look up the pv_record and add it to the cache for provides
        """
        query = "SELECT pv_record FROM provides_names WHERE pv_name = '%s'" % name
        pv_rec = self.db.fetch_one(query)
        if pv_rec:
            # add to the cache
            self.provides_cache[name] = pv_rec
            return pv_rec
        else:
            return False


    def get_provides_record(self, provides):
        """
        Function to lookup, add, and cache provides info
        """
        name = self.db.sanitize_string(provides)

        # first check the cache
        if name in self.provides_cache:
            return self.provides_cache[name]

        # not cached, check the database
        pv_rec = self.cache_get_provides(name)
        if pv_rec:
            return pv_rec

        # not cached, not in the db, add it
        query  = "INSERT INTO provides_names (pv_record, pv_name) VALUES (NULL, '%s')" % name
        pv_rec = self.db.do_query(query, True)
        if pv_rec:
            # add to the cache
            self.provides_cache[name] = pv_rec
            return pv_rec


    def add_provides(self, tag_id, record, file):
        """
        Function to add provides to the database
        """
        logging.debug('in Binary.add_provides(%s, %s, %s)' % (tag_id, record, file))

        list = commands.getoutput("rpm -qp --nosignature --provides " + self.rcommon.clean_shell(file))
        list = list.splitlines()
        for prov in list:
            if prov:
                self.rcommon.show_progress()
                if self.options.verbose:
                    print 'Provides: %s' % prov
                pv_rec = self.get_provides_record(prov.strip())
                query  = "INSERT INTO provides (t_record, p_record, pv_record) VALUES ('%s', '%s', '%s')" % (tag_id, record, pv_rec)
                result = self.db.do_query(query)


    def add_records(self, tag_id, record, file_list):
        """
        Function to add file records
        """
        logging.debug('in Binary.add_records(%s, %s, %s)' % (tag_id, record, file_list))

        for x in file_list.keys():
            self.rcommon.show_progress()
            if self.options.verbose:
                print 'File: %s' % file_list[x]['file']
            query  = "INSERT INTO files (t_record, p_record, u_record, g_record, files, f_is_suid, f_is_sgid, f_perms) VALUES ('%s', '%s', '%s', '%s', '%s', %d, %d, %s)" % (
                tag_id,
                record,
                self.get_user_record(file_list[x]['user']),
                self.get_group_record(file_list[x]['group']),
                self.db.sanitize_string(file_list[x]['file'].strip()),
                file_list[x]['is_suid'],
                file_list[x]['is_sgid'],
                file_list[x]['perms'])
            result = self.db.do_query(query)


    def add_binary_records(self, tag_id, record, rpm):
        """
        Function to add binary symbols and flags to the database
        """
        logging.debug('in Binary.add_binary_records(%s, %s, %s)' % (tag_id, record, rpm))

        cpio_dir = tempfile.mkdtemp()
        try:
            current_dir = os.getcwd()
            os.chdir(cpio_dir)
            # explode rpm
            command      = 'rpm2cpio "%s" | cpio -d -i 2>/dev/null' % rpm
            (rc, output) = commands.getstatusoutput(command)

            command      = 'find . -perm /u+x -type f'
            (rc, output) = commands.getstatusoutput(command)

            dir = output.split()
            logging.debug('dir is %s' % dir)
            for file in dir:
                if os.path.isfile(file):
                    logging.debug('checking file: %s' % file)
                    # executable files
                    if re.search('ELF', commands.getoutput('file ' + self.rcommon.clean_shell(file))):
                        # ELF binaries
                        flags   = self.get_binary_flags(file)
                        symbols = self.get_binary_symbols(file)
                        # need to change ./usr/sbin/foo to /usr/sbin/foo and look up the file record
                        nfile   = file[1:]
                        query   = "SELECT f_id FROM files WHERE t_record = %s AND p_record = %s AND files = '%s'" % (tag_id, record, nfile)
                        file_id = self.db.fetch_one(query)
                        self.add_flag_records(tag_id, file_id, record, flags)
                        self.add_symbol_records(tag_id, file_id, record, symbols)
            os.chdir(current_dir)
        finally:
            logging.debug('Removing temporary directory: %s...' % cpio_dir)
            try:
                shutil.rmtree(cpio_dir)
            except:
                # if we can't remove the directory, recursively chmod and try again
                os.system('chmod -R u+rwx ' + cpio_dir)
                shutil.rmtree(cpio_dir)


    def get_binary_symbols(self, file):
        """
        Function to get symbols from a binary file
        """
        symbols = []

        self.rcommon.show_progress()

        nm_output = commands.getoutput('nm -D -g ' + self.rcommon.clean_shell(file))
        nm_output = nm_output.split()
        for symbol in nm_output:
            if re.search('^[A-Za-z_]{2}.*', symbol):
                if symbol not in self.excluded_symbols:
                    # dump the __cxa* symbols
                    if not re.search('^__cxa', symbol):
                        symbols.append(symbol)

        return symbols


    def get_binary_flags(self, file):
        """
        Function to get binary flags from a file
        """
        flags = {'relro': 0, 'ssp': 0, 'nx': 0, 'pie': 0, 'fortify_source': 0}

        self.rcommon.show_progress()

        readelf_l = commands.getoutput('readelf -l ' + self.rcommon.clean_shell(file))
        readelf_d = commands.getoutput('readelf -d ' + self.rcommon.clean_shell(file))
        readelf_s = commands.getoutput('readelf -s ' + self.rcommon.clean_shell(file))
        readelf_h = commands.getoutput('readelf -h ' + self.rcommon.clean_shell(file))

        if re.search('GNU_RELRO', readelf_l):
            if re.search('BIND_NOW', readelf_d):
                # full RELRO
                flags['relro'] = 1
            else:
                # partial RELRO
                flags['relro'] = 2
        else:
            # no RELRO
            flags['relro'] = 0

        if re.search('__stack_chk_fail', readelf_s):
            # found
            flags['ssp'] = 1
        else:
            # none
            flags['ssp'] = 0

        if re.search('GNU_STACK.*RWE', readelf_l):
            # disabled
            flags['nx'] = 0
        else:
            # enabled
            flags['nx'] = 1

        if re.search('Type:( )+EXEC', readelf_h):
            # none
            flags['pie'] = 0
        elif re.search('Type:( )+DYN', readelf_h):
            if re.search('\(DEBUG\)', readelf_d):
                # enabled
                flags['pie'] = 1
            else:
                # DSO
                flags['pie'] = 2

        if re.search('_chk@GLIBC', readelf_s):
            # found
            flags['fortify_source'] = 1
        else:
            # not found
            flags['fortify_source'] = 0

        return flags


    def add_flag_records(self, tag_id, file_id, record, flags):
        """
        Function to add flag records to the database
        """
        logging.debug('in Binary.add_flag_records(%s, %s, %s, %s)' % (tag_id, file_id, record, flags))

        logging.debug('flags: %s' % flags)
        query  = "INSERT INTO flags (t_record, p_record, f_id, f_relro, f_ssp, f_pie, f_fortify, f_nx) VALUES ('%s', '%s', '%s', %d, %d, %d, %d, %d)" % (
            tag_id,
            record,
            file_id,
            flags['relro'],
            flags['ssp'],
            flags['pie'],
            flags['fortify_source'],
            flags['nx'])
        result = self.db.do_query(query)


    def cache_get_symbol(self, name):
        """
        Function to look up the s_record and add it to the cache for symbols
        """
        query = "SELECT s_record FROM symbol_names WHERE s_name = '%s'" % name
        s_rec = self.db.fetch_one(query)
        if s_rec:
            # add to the cache
            self.symbol_cache[name] = s_rec
            return s_rec
        else:
            return False


    def get_symbol_record(self, symbol):
        """
        Function to lookup, add, and cache symbols info
        """
        name = self.db.sanitize_string(symbol)

        # first check the cache
        if name in self.symbol_cache:
            return self.symbol_cache[name]

        # not cached, check the database
        s_rec = self.cache_get_symbol(name)
        if s_rec:
            return s_rec

        # not cached, not in the db, add it
        query = "INSERT INTO symbol_names (s_record, s_name) VALUES (NULL, '%s')" % name
        s_rec = self.db.do_query(query, True)
        if s_rec:
            # add to the cache
            self.symbol_cache[name] = s_rec
            return s_rec


    def add_symbol_records(self, tag_id, file_id, record, symbols):
        """
        Function to add symbol records to the database
        """
        logging.debug('in Binary.add_symbol_records(%s, %s, %s, %s)' % (tag_id, file_id, record, symbols))

        for symbol in symbols:
            s_rec = self.get_symbol_record(symbol)
            query  = "INSERT INTO symbols (t_record, p_record, f_id, s_record) VALUES ('%s', '%s', '%s', '%s')" % (
                tag_id,
                record,
                file_id,
                s_rec)
            result = self.db.do_query(query)


    def convert_flags(self, flags):
        """
        Convert numeric representation of flags (from the database) to human
        readable form, dropping the prefix (i.e. f_relro becomes relro)
        """
        newflags = {}

        if flags['f_relro'] == 1:
            newflags['relro'] = "full"
        elif flags['f_relro'] == 2:
            newflags['relro'] = "partial"
        else:
            newflags['relro'] = "none"

        if flags['f_ssp'] == 1:
            newflags['ssp'] = "found"
        else:
            newflags['ssp'] = "not found"

        if flags['f_nx'] == 1:
            newflags['nx'] = "enabled"
        else:
            newflags['nx'] = "disabled"

        if flags['f_pie'] == 2:
            newflags['pie'] = "DSO"
        elif flags['f_pie'] == 1:
            newflags['pie'] = "enabled"
        else:
            newflags['pie'] = "none"

        if flags['f_fortify'] == 1:
            newflags['fortify'] = "found"
        else:
            newflags['fortify'] = "not found"

        return(newflags)


    def list_updates(self, tag):
        """
        Function to list packages that have been imported due to being in the updates directory
        """
        logging.debug('in Binary.list_updates(%s)' % tag)

        print 'Updated packages in tag %s:\n' % tag

        query   = "SELECT t_record FROM tags WHERE tag = '%s' LIMIT 1" % self.db.sanitize_string(tag)
        tag_id  = self.db.fetch_one(query)

        query   = "SELECT p_fullname FROM packages WHERE t_record = %s AND p_update = 1 ORDER BY p_fullname ASC" % tag_id
        results = self.db.fetch_all(query)
        if results:
            for xrow in results:
                print '%s' % xrow['p_fullname']
        else:
            print 'No results found.'


    def show_sxid(self, type, tag):
        """
        Function to list all suid or sgid files per tag
        """
        logging.debug('in Binary.show_sxid(%s, %s)' % (type, tag))

        print 'Searching for %s files in tag %s\n' % (type.upper(), tag)

        query   = "SELECT t_record FROM tags WHERE tag = '%s' LIMIT 1" % self.db.sanitize_string(tag)
        tag_id  = self.db.fetch_one(query)

        if not tag_id:
            print 'Invalid tag: %s' % tag
            sys.exit(1)

        if type == 'suid':
            db_col = 'f_is_suid'
        elif type == 'sgid':
            db_col = 'f_is_sgid'

        query   = "SELECT p_package, files, f_user, f_group, f_perms FROM files JOIN packages ON (files.p_record = packages.p_record) WHERE %s = 1 AND files.t_record = %s ORDER BY p_package ASC" % (db_col, tag_id)
        results = self.db.fetch_all(query)
        if results:
            for xrow in results:
                print '%s: %s [%s:%s mode %s]' % (xrow['p_package'], xrow['files'], xrow['f_user'], xrow['f_group'], xrow['f_perms'])
        else:
            print 'No results found.'
