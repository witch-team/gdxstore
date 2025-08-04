#!/usr/bin/env python3
"""
Stores gdx result files divided by commits.
Files that can be reproduced with a make command are directly stored,
provided that their execution start time is after the latest file change
for the present commit.
Files that were produced with commands other than make ones can be 
stored, provided that the recipe to make them is added to a custom makefile.

Example usage:
python gdxstore.py -s results_ssp2_bau.gdx --storage-folder /data/cmcc/mg01025/witch_results

Can also do it for multiple files:
python gdxstore.py -s results_ssp2_bau.gdx results_ssp2_curpol.gdx --storage-folder /data/cmcc/mg01025/witch_results

It is also possible to have a log including the stored files:
python gdxstore.py --log --storage-folder /data/cmcc/mg01025/witch_results

And to produce a gdxdiff file, like this:
python gdxstore.py -d results_ssp2_ctax_200.gdx --commit 353d204b05029d94cf4d82 --storage-folder /data/cmcc/mg01025/witch_results/
This compares the current version of the results with the one of the specified commit

TODO: find a clean way to handle the data_$(n) folder
"""

import subprocess
import os
import stat
import time
from datetime import datetime
import shutil
import sys
from configparser import RawConfigParser
import argparse
from pathlib import Path
from typing import List, Optional

def run_command(command):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            universal_newlines=True,
            check=False
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GDXStoreError("Command failed: {}\nError: {}".format(command, e.stderr))
        
# old version, incompatible with python 3.6, the version on juno
# def run_command(self, command: str) -> str:
#     """Run a shell command and return output."""
#     try:
#         result = subprocess.run(
#             command,
#             capture_output=True,
#             shell=True,
#             text=True,
#             check=False
#         )
#         return result.stdout.strip()
#     except subprocess.CalledProcessError as e:
#         raise GDXStoreError(f"Command failed: {command}\nError: {e.stderr}")

def get_commit_folder_name(commit: str) -> str:
    """Get 8-character hash of the commit (=folder name)"""
    return run_command('git rev-parse --short=8 ' + str(commit))


class GDXStoreError(Exception):
    """Custom exception for GDX storage errors."""
    pass


class GDXStore:
    """Handles storage of GDX files with git version control."""
    
    def __init__(self, file_to_store: str, 
                       storage_folder: str = './witch-results',
                       recipe = None):
        self.file_to_store = file_to_store
        self.storage_folder = Path(storage_folder)
        self.recipe = recipe

        self.commit_hash = self.compute_commit_hash()
        self.run_name = self.compute_run_name()
                
        # Create destination directory
        self.dest_dir = self.storage_folder / self.commit_hash
        try:
            self.dest_dir.mkdir(parents=True)
        except FileExistsError:
            pass
    
    def compute_commit_hash(self) -> str:
        """Get the short hash of the latest commit."""
        commit_hash = run_command("git rev-parse --short HEAD")
        if not commit_hash:
            raise GDXStoreError("Could not get commit hash")
        print(f"Current commit: {commit_hash}")
        return commit_hash

    def compute_run_name(self) -> str:    
        """Extract run name from target filename"""
        return self.file_to_store.split('_', maxsplit=1)[1].split('.')[0]

    def get_make_targets(self, options: str = "") -> List[str]:
        """Get list of GDX files that can be reproduced with make."""
        command = (
            "make -qp " + options + 
            " | awk -F':' '/^[a-zA-Z0-9][^$#\\/\\t=]*:.*.gdx([^=]|$)/ "
            "{split($2,A,/ /);for(i in A)print A[i]}'"
        )
        output = run_command(command)
        return [f for f in output.split() if f.endswith('.gdx')]
    
    def check_file_reproducible(self) -> None:
        """Check if the target file is reproducible through makefiles."""
        make_targets = self.get_make_targets()
        if self.file_to_store not in make_targets:
            if self.recipe is not None:
                if Path(self.recipe).is_file():
                    print(f"✓ {self.file_to_store} is not among make targets, but recipe {self.recipe} has been specified.")
                    recipe_dir = self.storage_folder / self.commit_hash / "recipes"
                    try:
                        recipe_dir.mkdir(parents=True)
                    except FileExistsError:
                        pass
                    dest_file = recipe_dir / self.recipe
                    shutil.copy2(self.recipe, dest_file)
                    print(f"✓ {self.recipe} has been copied to {str(recipe_dir)}.")
                    recipe_file = self.storage_folder / self.commit_hash / "recipes.txt"
                    if not recipe_file.is_file():
                        with open(recipe_file, 'w') as f:
                            f.write('# List of shell scripts/makefiles for stored results that are not make targets\n\n')
                    with open(recipe_file, 'a') as f:
                        f.write(f'{self.file_to_store}: {self.recipe}\n') 
                else:
                    raise GDXStoreError(f"{self.file_to_store} is not among make targets, a recipe has been specified, but there is no {self.recipe} file.\n"
                                        f"Please provide a valid recipe.")
            else:
                raise GDXStoreError(f"{self.file_to_store} is not among make targets, and no recipe has been specified.\n"
                                    F"Rerun the code with the --recipe flag pointing to a script to reproduce the result.")

            # old version with makefiles
            #custom_makefile = Path(self.storage_folder / self.commit_hash / "Makefile")
            # # Search among custom targets
            # custom_make_targets = self.get_make_targets(options = "--file=" + str(custom_makefile))
            # if self.file_to_store in custom_make_targets:
            #     print(
            #         f'Found a recipe for {self.file_to_store} in the custom makefile {str(custom_makefile)}\n'
            #         f'Double check that the recipe is valid! (press any key to confirm)'
            #     )
            #     input("")
            # else:
            #     print(
            #         f'{self.file_to_store} is not reproducible through makefiles.\n'
            #         f'Would you like to store the recipe for {self.file_to_store} in the archived makefile?\n'
            #         f'1. Yes\n'
            #         f'2. No\n'
            #     )
            #     add_custom_recipe = input()
            #     while (add_custom_recipe!='1') and (add_custom_recipe!='2'):
            #         print(f'Please select one of the 2 options.\n')
            #         add_custom_recipe = input()
            #     if (add_custom_recipe=='1'):
            #         custom_makefile = Path(self.storage_folder / self.commit_hash / "Makefile")
            #         print('created path')
            #         if custom_makefile.is_file():
            #             print(f'A custom makefile already exists at {str(custom_makefile)}\n')
            #         else:
            #             print('trying to reach makefile')
            #             with open(custom_makefile, 'w') as f:
            #                 print('writing to makefile')
            #                 f.write(f'# Custom recipes for the result files stored in this folder\n')
            #             print(f'A custom makefile has been created at {str(custom_makefile)}\n')
            #         with open(custom_makefile, 'a') as f:
            #             f.write(f'\n{self.run_name}={self.file_to_store}\n')
            #             f.write(f'{self.run_name}: $({self.run_name})\n')
            #             f.write(f'$({self.run_name}): # Insert dependencies here\n')
            #             f.write(f'    # Insert command here\n')
            #         print(f'Lines have been added to the custom makefile. Please edit it')
            #     exit()
        else:
            print(f"✓ {self.file_to_store} is reproducible through makefiles")
    
    def check_uncommitted_changes(self) -> None:
        """Check for uncommitted changes in git."""
        uncommitted_files = run_command("git diff --name-only").split()
        if uncommitted_files:
            raise GDXStoreError(
                f'There are uncommitted changes: {uncommitted_files}\n'
                'Please commit or stash changes before storing results.'
            )
        print("✓ No uncommitted changes found")
    
    def get_latest_source_change(self) -> tuple:
        """Get the latest modified file from the last commit and its timestamp."""
        try:
            committed_files = run_command("git show --pretty=\"\" --name-only").split()

            file_mtimes = [os.stat(f)[stat.ST_MTIME] for f in committed_files]
            # Find argmax without numpy to reduce dependencies
            latest_idx = [i for i in range(len(file_mtimes)) if file_mtimes[i]==max(file_mtimes)][0]
            # latest_idx = np.argmax(file_mtimes)
            latest_file = committed_files[latest_idx]
            latest_time = file_mtimes[latest_idx]
            
            print(f"Latest modified file: {latest_file}")
            print(f"Modified on: {time.ctime(latest_time)}")
            
            return latest_file, latest_time
            
        except (OSError, IndexError) as e:
            raise GDXStoreError(f"Error getting file modification times: {e}")
    
    def get_simulation_start_time(self) -> float:
        """Extract simulation start time from error file."""
        # Generate error filename based on run name
        error_filename = f'errors_{self.run_name}.txt'
        
        try:
            with open(error_filename, 'r') as f:
                header = f.readline().strip()
            
            if not header:
                raise GDXStoreError(f"Empty or invalid error file: {error_filename}")
            
            # Extract timestamp from header
            start_time_str = header.split(' ', maxsplit=1)[1]
            dt = datetime.strptime(start_time_str, "%m/%d/%y %H:%M:%S")
            start_timestamp = dt.timestamp()
            
            print(f"Simulation started on: {time.ctime(start_timestamp)}")
            return start_timestamp
            
        except FileNotFoundError:
            raise GDXStoreError(f"Can't find {error_filename}. This is needed to determine the execution time")
        except (IndexError, ValueError) as e:
            raise GDXStoreError(f"Error parsing timestamp from {error_filename}: {e}")
    
    def validate_timing(self, start_timestamp: float, latest_source_time: float) -> None:
        """Validate that simulation started after latest source change."""
        if start_timestamp < latest_source_time:
            time_diff = latest_source_time - start_timestamp
            raise GDXStoreError(
                f"Execution started before the latest file change!\n"
                f"Latest change: {time.ctime(latest_source_time)}\n"
                f"Execution start: {time.ctime(start_timestamp)}"
            )
        print("✓ Execution time > Latest change!")
    
    def store_file(self, commit_hash: str) -> None:
        """Store the GDX file in the storage folder."""
        if not os.path.exists(self.file_to_store):
            raise GDXStoreError(f"Target file does not exist: {self.file_to_store}")
        
        # Copy file
        dest_file = self.dest_dir / self.file_to_store
        shutil.copy2(self.file_to_store, dest_file)
        
        print(f"✓ File stored: {dest_file}")
    

    def run(self, validate_timing: bool = True) -> None:
        """Run the complete storage process."""
        print(f"Starting GDX storage process for: {self.file_to_store}")
        print("=" * 50)
        
        try:
            # Validation steps
            # Check if file is already stored
            if (self.storage_folder / self.commit_hash / self.file_to_store).is_file():
                raise GDXStoreError(f"{self.file_to_store} has already been stored!")
            self.check_file_reproducible()
            self.check_uncommitted_changes()
            
            # Get timing information
            latest_file, latest_source_time = self.get_latest_source_change()
            start_timestamp = self.get_simulation_start_time()
            
            # Validate timing if requested
            if validate_timing:
                self.validate_timing(start_timestamp, latest_source_time)
            
            # Store the file
            commit_hash = self.commit_hash
            self.store_file(commit_hash)
            
            print("=" * 50)
            print("✓ GDX storage completed successfully")
            
        except GDXStoreError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            sys.exit(1)
    

def main():
    # Default settings
    conf = RawConfigParser()
    conf.read('config.ini')
    default_storage_folder = conf['storage'].get('storage_folder')

    # Command line options
    parser = argparse.ArgumentParser(description='Store and inspect GDX files')
    parser.add_argument('-s', action='store_true',
                       help='Store a file')
    parser.add_argument('-d', action='store_true',
                       help='Run gdxdiff')
    parser.add_argument('files', nargs='*',
                       help='GDX file(s) to store or compare')
    parser.add_argument('--storage-folder', default=default_storage_folder,
                       help='Storage folder path (default set in config.ini)')
    parser.add_argument('--no-timing-validation', action='store_true',
                       help='Skip timing validation')
    parser.add_argument('--log', action='store_true',
                       help='Show the git log with stored files for each commit')
    parser.add_argument('--recipe', help='Script to produce the stored result, if it is not a makefile target')
    parser.add_argument('--commit', nargs='*',
                       help='Commit(s) to compare')

    args = parser.parse_args()

    # Storage
    if args.s:
        for file in args.files:    
            print('\n')
            store = GDXStore(file, args.storage_folder, args.recipe)
            store.run(validate_timing=not args.no_timing_validation)
    # Diff
    if args.d:
        if len(args.commit)==1:
            commit = args.commit[0]
            commit_folder_name = get_commit_folder_name(commit)
            committed_file_path = Path(args.storage_folder) / Path(commit_folder_name) / Path(args.files[0])
            if committed_file_path.is_file():
                print(f"✓ Found stored file at {str(committed_file_path)}\n")
                print("Running gdxdiff...")
                diffile_name = 'diffile_' + args.files[0]
                gdxdiff_out = run_command('gdxdiff ' + 
                                          args.files[0] + ' ' + 
                                          str(committed_file_path) + 
                                          ' ' + diffile_name)
                # TODO: print a summary of the output?
        else:
            raise NotImplementedError()
    # Log
    if args.log:
        from pydoc import pager
        git_history = run_command('git log --since=2025-07-01').split("\n")
        stored_files = None
        gdxstore_history = git_history.copy()
        n_inserted = 0
        for (ii, line) in enumerate(git_history):
            words = line.split(' ')
            if words[0]=="commit": 
                commit = get_commit_folder_name(words[1])
                if stored_files is not None:
                    gdxstore_history.insert(ii-1+n_inserted, "\nStored files:")
                    gdxstore_history.insert(ii+n_inserted, stored_files)
                    n_inserted += 2
                    stored_files = None
                try:
                    stored_ls = set(os.listdir(Path(args.storage_folder) / Path(commit)))
                    stored_ls.discard('recipes')
                    stored_ls.discard('recipes.txt')
                    if len(stored_ls)>0:
                        stored_files = '\n'.join(stored_ls)
                except: 
                    pass
        gdxstore_history = '\n'.join(gdxstore_history)
        pager(gdxstore_history)


if __name__ == '__main__':
    main()
