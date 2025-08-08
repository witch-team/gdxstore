# gdxstore
A storage and version control tool for WITCH result files.

## Installation
Add the `gdxstore/source` directory to your PATH.

Using the setup.py file would require using a virtual environment on HPC. 
I prefer to avoid this for now.

Then copy the configuration file to your WITCH installation folder. For example:

`cp config.ini-example ../witch/config.ini`

and replace `<your-username>`, or change the whole path if you prefer.
This is the path where all the files will be stored. A new subfolder will be created
for each commit with files to store.
The plan is to add more global options to `config.ini`, such as default gdxdiff tolerances
and the log history start date.

## Usage examples
- Store a file:
  
`python gdxstore.py -s results_ssp2_bau.gdx`

The code checks that the file is a makefile target. If not, it asks the user to provide
a script used to produce it, so that it can be stored along with the file for reproducibility.
It then checks that there are no uncommitted changes to the code. If there are any, it asks the 
user whether a patch with the changes should be created. In this case, time and date of the run
are appended to the file name and to the patch name.
The code finally checks that the computation started after the last source file change. If this is not true,
it raises an error and doesn't store it. 
In case you are sure that the result was produced with the current version of the code,
even if the latest change is later than the run start time, you can avoid this check by adding flag
`no-timing-validation` to the command. Something like this can happen if, for example, you make some
changes to the code while the code is running and then you revert them.
- Display the git log including the list of stored files for each commit:

`python gdxstore.py --log`
- Compare the current version of a result file with one from a previous commit:
  
`python gdxstore.py -d results_ssp2_ctax_200.gdx --commit 353d204b05029d94cf4d82`

This calls gdxdiff. TODO: add gdxdiff options.
- Override the default storage directory:
  
`python gdxstore.py -s results_ssp2_bau.gdx --storage-folder ../temp_results`

