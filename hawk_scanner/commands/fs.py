import argparse
from google.cloud import storage
from rich.console import Console
from hawk_scanner.internals import system
import os
import concurrent.futures
import time

def process_file(file_path, key, results):
    matches = system.read_match_strings(file_path, 'fs')
    file_data = system.getFileData(file_path)
    if matches:
        for match in matches:
            results.append({
                'host': 'This PC',
                'file_path': file_path,
                'pattern_name': match['pattern_name'],
                'matches': match['matches'],
                'sample_text': match['sample_text'],
                'profile': key,
                'data_source': 'fs',
                'file_data': file_data
            })

def execute(args):
    results = []
    connections = system.get_connection()
    if 'sources' in connections:
        sources_config = connections['sources']
        fs_config = sources_config.get('fs')
        if fs_config:
            for key, config in fs_config.items():
                if 'path' not in config:
                    system.print_error(f"Path not found in fs profile '{key}'")
                    continue
                path = config.get('path')
                if not os.path.exists(path):
                    system.print_error(f"Path '{path}' does not exist")
                
                exclude_patterns = fs_config.get(key, {}).get('exclude_patterns', [])
                start_time = time.time()
                files = system.list_all_files_iteratively(path, exclude_patterns)
                
                # Use ThreadPoolExecutor for parallel processing
                file_count = 0
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = []
                    for file_path in files:
                        file_count += 1
                        futures.append(executor.submit(process_file, file_path, key, results))
                    
                    # Wait for all tasks to complete
                    concurrent.futures.wait(futures)
                end_time = time.time()
                system.print_info(f"Time taken to analyze {file_count} files: {end_time - start_time} seconds")
        else:
            system.print_error("No filesystem 'fs' connection details found in connection.yml")
    else:
        system.print_error("No 'sources' section found in connection.yml")
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Add your command-line arguments here if needed
    args = parser.parse_args()
    results = execute(args)
    # Handle results as needed
