# import required libraries
import sys
from os import listdir
from os.path import isfile, join
import h5py as h5
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Read H5 file

mypath =sys.argv[1].split("=")[1]
# gets list of files
list_of_files = [f for f in listdir(mypath) if isfile(join(mypath, f))]
# removes anything but h5
list_of_files = [f for f in list_of_files if (".h5" in f)]

print("Total of %d files will be analyse. Files found under the folder %s: " % (len(list_of_files), mypath))
for i, name_h5_file in enumerate(list_of_files):
    print("%d: %s " % (i,name_h5_file))

list_of_missing_metadata = []
need_info = True
for file_h5_output in list_of_files:
    print(mypath+file_h5_output)
    f = h5.File(mypath+file_h5_output, "r")
    # Get and print list of datasets within the H5 file
    datasetNames = [n for n in f.keys()]
    # opens the database
    for n in datasetNames:
        # gets the detector dataset
        detector = f[n]
        # for the metadata inside detector datagroup
        for metadata in detector.keys():
            # looking inside missing packets 2x 64bits
            if "missing_packets_" in metadata:
                if need_info == True:
                    print("Data Description of the metadata: ", detector[metadata], " \n\n ")
                    need_info = False
                missing_metadata = detector[metadata]

                list_of_missing_metadata.append(missing_metadata[()])
    # close the h5 file
    f.close()

meta_df = None
# treat metadata info
for index in range(0, len(list_of_missing_metadata)):
    list_of_missing_metadata[index] = list_of_missing_metadata[index][0]
meta_df = pd.DataFrame((list_of_missing_metadata))


# empty rows:
success_modules = []
lost_modules = []
for i in meta_df:
    # nothing was missing, max == 0
    if meta_df[i].describe()['max'] == 0:
        success_modules.append(i)
    else:
        lost_modules.append(i)
print(" %d half modules received everything: %s " %(len(success_modules), success_modules))
print(" %d half modules had something lost: %s " %(len(lost_modules), lost_modules))


# description of the dataframe
print(meta_df.describe())
# brief print out of the datafram
print(meta_df)

bitwise_cols = []
# bitwise analysis for each module
print("MODULE INDEX:", end="")
for module_index in meta_df:
    # for each module
    print(" %d" % module_index, end="")
    list_new_entries = []
    for entry in meta_df[module_index]:
        #converts to bit
        list_new_entries.append('{0:64b}'.format(entry))
    meta_df[str(module_index)+"_bitwise"] = list_new_entries
print("")

meta_df.to_csv(mypath+'analysis.csv')

