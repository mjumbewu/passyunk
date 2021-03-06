from __future__ import print_function

import csv
import os
import sys

__author__ = 'tom.swanson'

cwd = os.path.dirname(__file__)
cwd += '/pdata'
#cwd = cwd.replace('\\','/')
cl_file = 'centerline'


def csv_path(file_name):
    return os.path.join(cwd, file_name + '.csv').replace('\\','/')


cl_basename = {}
cl_list = []
cl_name = {}


class Centerline:
    def __init__(self, row):
        self.pre = row[0].strip()
        self.name = row[1].strip()
        self.suffix = row[2].strip()
        self.post = row[3].strip()
        self.from_left = int(row[4])
        self.to_left = int(row[5])
        self.from_right = int(row[6])
        self.to_right = int(row[7])
        self.st_code = row[8]
        self.seg_id = row[9]
        self.responsibility = row[10].strip()
        self.base = '{} {} {} {}'.format(self.pre, self.name, self.suffix, self.post)
        self.base = ' '.join(self.base.split())
        self.oeb_right = oeb(self.from_right, self.to_right)
        self.oeb_left = oeb(self.from_left, self.to_left)


class NameOnly:
    def __init__(self, row):
        self.name = row[0]
        self.low = row[1]
        self.high = row[2]

def test_cl_file():
    path = csv_path(cl_file)
    return os.path.isfile(path)

def create_cl_lookup():
    path = csv_path(cl_file)
    f = open(path, 'r')
    i = 0
    j = 0
    jbase = 0

    try:
        reader = csv.reader(f)
        p_name = ''
        c_name = ''
        p_base = ''
        c_base = ''

        for row in reader:
            if i == 0:
                i += 1
                continue
            r = Centerline(row)
            if i == 0:
                rp = r
            c_name = r.name
            c_base = r.base

            if c_name != p_name and i != 0:
                ack = [p_name, j - 1, i - 1]
                r2 = NameOnly(ack)
                cl_name[p_name] = r2
                j = i

            if c_base != p_base and i != 0:
                ack = [p_base, jbase - 1, i - 1]
                r2 = NameOnly(ack)
                cl_basename[p_base] = r2
                jbase = i

            cl_list.append(r)
            rp = r
            p_name = c_name
            p_base = c_base
            i += 1

    except IOError:
        print('Error opening ' + path, sys.exc_info()[0])
    ack = [p_base, jbase - 1, i - 1]
    r2 = NameOnly(ack)
    cl_basename[p_base] = r2

    validate_cl_basename()

    f.close()
    return


def oeb(fr, to):
    ret = 'U'
    if fr == '' or fr == '0' or to == '' or to == '0':
        return 'U'

    if fr % 2 == 0:
        ret = 'E'
    else:
        ret = 'O'
    if to % 2 == 0:
        ret_to = 'E'
    else:
        ret_to = 'O'

    if ret != ret_to:
        return 'B'

    return ret


def validate_cl_basename():
    for r in cl_basename:
        row = cl_basename[r]
        row_list = cl_list[row.low:row.high]
        name = {}
        for st in row_list:
            name[st.base] = st.base
        if len(name) > 1:
            for ack in name:
                print(ack)


def is_cl_base(test):
    try:
        name = cl_basename[test]
    except KeyError:
        row = []
        # row.append([' ', 0, 0])
        return row
    return cl_list[name.low:name.high]


def is_cl_name(test):
    try:
        name = cl_name[test]
    except KeyError:
        row = []
        # row.append([' ', 0, 0])
        return row
    return cl_list[name.low:name.high]


def get_cl_info(address, input_):
    cl_list = is_cl_base(address.street.full)

    if len(cl_list) > 0:
        mlist = []
        number_distance = 1000000
        addr_near = 0
        number_distance_rec = {}
        for row in cl_list:
            if row.from_left <= address.address.low_num and row.to_left >= address.address.low_num and row.oeb_left == address.address.parity:
                mlist.append(row)
            elif row.from_right <= address.address.low_num and row.to_right >= address.address.low_num and row.oeb_right == address.address.parity:
                mlist.append(row)
            else:
                if row.from_left != 0 and abs(row.from_left - address.address.low_num) < number_distance:
                    number_distance = abs(row.from_left - address.address.low_num)
                    number_distance_rec = row
                    addr_near = row.from_left
                if row.from_left != 0 and abs(row.from_right - address.address.low_num) < number_distance:
                    number_distance = abs(row.from_right - address.address.low_num)
                    number_distance_rec = row
                    addr_near = row.from_right
                if row.from_left != 0 and abs(address.address.low_num - row.to_left) < number_distance:
                    number_distance = abs(address.address.low_num - row.to_left)
                    number_distance_rec = row
                    addr_near = row.to_left
                if row.from_left != 0 and abs(address.address.low_num - row.to_right) < number_distance:
                    number_distance = abs(address.address.low_num - row.to_right)
                    number_distance_rec = row
                    addr_near = row.to_right

        # good street name but no matching address range
        if len(mlist) == 0 and number_distance != 1000000:
            address.st_code = number_distance_rec.st_code
            address.seg_id =number_distance_rec.seg_id
            address.responsibility = number_distance_rec.responsibility
            address.cl_addr_match = 'RANGE:'+str(number_distance)
            address.address.full = str(addr_near)
            return

        if len(mlist) == 0:
            address.st_code = row.st_code
            address.cl_addr_match = 'MATCH TO STREET WITH NO ADDR RANGE'
            return

        # Exact Match
        if len(mlist) == 1:
            address.st_code = mlist[0].st_code
            address.seg_id = mlist[0].seg_id
            address.responsibility = mlist[0].responsibility
            address.cl_addr_match = 'A'
            return

        # Exact Street match, multiple range matches, return the count of matches
        if len(mlist) > 1:
            address.st_code = row.st_code
            address.cl_addr_match = 'AM'
            # address.cl_addr_match = str(len(mlist))
            return

    cl_list = is_cl_name(address.street.name)

    if len(cl_list) > 0:
        mlist = []
        for row in cl_list:
            if row.from_left <= address.address.low_num and row.to_left >= address.address.low_num and row.oeb_left == address.address.parity:
                if (address.street.predir != '' and address.street.predir == row.pre) or (
                                address.street.predir == '' and row.pre == '') or (
                                address.street.predir == '' and row.pre != '') or (
                                address.street.predir != '' and row.pre == ''):
                    if (address.street.postdir != '' and address.street.postdir == row.post) or (
                                    address.street.postdir == '' and row.post == '') or (
                                    address.street.postdir == '' and row.post != '') or (
                                    address.street.postdir != '' and row.post == ''):
                        if (address.street.suffix != '' and address.street.suffix == row.suffix) or (
                                        address.street.suffix == '' and row.suffix == '') or (
                                        address.street.suffix == '' and row.suffix != '') or (
                                        address.street.suffix != '' and row.suffix == ''):
                            mlist.append(row)
            elif row.from_right <= address.address.low_num and row.to_right >= address.address.low_num and row.oeb_right == address.address.parity:
                if (address.street.predir != '' and address.street.predir == row.pre) or (
                                address.street.predir == '' and row.pre == '') or (
                                address.street.predir == '' and row.pre != '') or (
                                address.street.predir != '' and row.pre == ''):
                    if (address.street.postdir != '' and address.street.postdir == row.post) or (
                                    address.street.postdir == '' and row.post == '') or (
                                    address.street.postdir == '' and row.post != '') or (
                                    address.street.postdir != '' and row.post == ''):
                        if (address.street.suffix != '' and address.street.suffix == row.suffix) or (
                                        address.street.suffix == '' and row.suffix == '') or (
                                        address.street.suffix == '' and row.suffix != '') or (
                                        address.street.suffix != '' and row.suffix == ''):
                            mlist.append(row)

        # good street name but no matching address range
        if len(mlist) == 0:
            address.cl_addr_match = 'S2'
            return

        if len(mlist) == 1:
            match = 'B'
            if address.street.predir != mlist[0].pre:
                match += ' Pre'
                address.street.predir = mlist[0].pre
            if address.street.postdir != mlist[0].post:
                match += ' Post'
                address.street.postdir = mlist[0].post
            if address.street.suffix != mlist[0].suffix:
                match += ' Suffix'
                address.street.suffix = mlist[0].suffix
            address.st_code = mlist[0].st_code
            address.seg_id = mlist[0].seg_id
            address.responsibility = mlist[0].responsibility
            address.cl_addr_match = match
        # need to resolve dir and/or suffix
        if len(mlist) > 1:
            address.st_code = row.st_code
            address.cl_addr_match = 'MULTI'  # str(len(mlist))
            return
