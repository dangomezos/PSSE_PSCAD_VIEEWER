import os
import re
import math
import pandas as pd
from functools import reduce
from pathlib import PurePath


def _read_pscad_header(path, file_name):
    ''' Parse the .inf file of a PSCAD case and return:
        - header: ordered list of column names (including one 'time' per .out chunk)
        - last_col: number of data columns stored in each .out chunk
        - n_files: number of .out chunks exported for this case '''

    inf_ex = '.inf'
    n_col = 11  # Number of columns that each .out chunk has (1 time + up to 10 variables)

    INF_path = PurePath(path, file_name + inf_ex)

    with open(INF_path) as myfile:
        lines = myfile.readlines()

    n_var = len(lines)                          # Number of PSCAD Variables
    n_files = int(math.ceil(n_var / 10.0))      # Number of .out Files exported (the floating is important)
    n_var_tot = n_var + n_files                 # Number of variables INCLUDING additional time column FOR EACH .OUT
    n_var_last = n_var_tot - (n_files - 1) * n_col  # Number of variables in the last file

    last_col = [0] * n_files
    for file_ in range(0, n_files):
        last_col[file_] = n_col if file_ != n_files - 1 else n_var_last

    pattern = 'Desc="(.*?)"'    # Pattern that holds the variable name
    pattern2 = 'Group="(.*?)"'  # Pattern that holds the canvas/group name of the variable
    header = [0] * n_var_tot

    b = 0  # to "freeze" the time when storing the "TIME"

    # "For" Logic: each file can take 11 variables, and the first one is TIME
    # so this "for" writes time if it is the time column, or takes the header from
    # the array "header"
    for var in range(0, n_var_tot):
        if (var == 0) | (var % 11 == 0):  # if it is the first value of all files, store the time name
            header[var] = 'time'
            b = b - 1
        else:
            header[var] = re.search(pattern, lines[b]).group(1)
            header[var] = header[var].replace(" ", "_")

            header2 = re.search(pattern2, lines[b]).group(1)  # canvas where the variable lives
            header[var] = f"{header[var]}_{header2}"          # concatenate variable + canvas name

        b = b + 1

    return header, last_col, n_files


def _out_chunk_paths(path, file_name, n_files):
    ''' Build the paths of the n_files .out chunks exported by PSCAD for this case '''
    out_ex = '.out'
    OUT_path = [0] * n_files
    for ii in range(0, n_files):
        if ii < 9:
            OUT_name = "_0" + str(ii + 1) + out_ex  # "_01.out", "_02.out", ...
        else:
            OUT_name = "_" + str(ii + 1) + out_ex   # "_10.out", "_11.out", ...
        OUT_path[ii] = PurePath(path, file_name + OUT_name)
    return OUT_path


def read_pscad_case(path, file_name, del_out=False):
    ''' Read every .out chunk exported by PSCAD for a case (using the matching
    .inf as header dictionary) and return a single merged DataFrame, entirely
    in memory - no .csv is written to disk. '''

    header, last_col, n_files = _read_pscad_header(path, file_name)
    OUT_path = _out_chunk_paths(path, file_name, n_files)

    # Read all of the .out chunks
    dff = []
    for out_path in OUT_path:
        dff.append(pd.read_csv(out_path, sep=r'\s+', header=None))
        if del_out:
            os.remove(out_path)

    # Rename the header of each chunk (which is now 0,1,2,3,4...) for the names in 'header'
    jj = 0
    for file_ in range(0, n_files):
        for ii in range(0, last_col[file_]):
            dff[file_].rename(columns={ii: header[ii + jj]}, inplace=True)
        jj = jj + 11

    # Merge all of the chunks (2 by 2) using the column 'time' as reference
    df_merged = reduce(lambda left, right: pd.merge(left, right, on='time'), dff)

    return df_merged


def resolve_pscad_case(filepath):
    ''' Given any file that belongs to a PSCAD case (its .inf, or one of the
    numbered .out chunks), return (path, file_name) usable with
    read_pscad_case()/PSCADVar(). Raises ValueError if filepath doesn't look
    like a PSCAD case file. '''

    p = PurePath(filepath)
    path = str(p.parent)
    name = p.stem
    ext = p.suffix.lower()

    if ext == '.inf':
        return path, name

    if ext == '.out':
        m = re.match(r'^(.*)_\d{2,}$', name)  # strip trailing "_01", "_02", ...
        file_name = m.group(1) if m else name
        return path, file_name

    raise ValueError(f"'{filepath}' no parece un archivo de caso PSCAD (.inf/.out)")


def PSCADVar(path, file_name, del_out=False):

    ''' Function which will compile all the .out files exported by PSCAD in a .csv file.
    Kept for backwards compatibility with existing scripts/notebooks. '''

    csv_ex = '.csv'
    CSV_path = PurePath(path, file_name + csv_ex)  # Replaces the ending .inf with .csv

    df_merged = read_pscad_case(path, file_name, del_out=del_out)

    # Storage all the dataframe into one csv file with header
    df_merged.to_csv(CSV_path, index=False)

    return
