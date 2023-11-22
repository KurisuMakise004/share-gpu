from pathlib import Path
import yaml
import subprocess
import time
script_content="""
#!/usr/bin/env python3
try:
    number = int(input("Enter the number of GPUs you want to use [0]: ") or 0)
except ValueError:
    number = 0

with open('/var/assign', 'w') as file:
    file.write(str(number))
"""

def get_gpus_memory_usage():
    """Gets the GPU memory usage using nvidia-smi command."""
    try:
        # Execute the nvidia-smi command and capture the output
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=index,memory.used", "--format=csv,noheader,nounits"]).decode()

        # Parse the output to extract GPU index and memory usage
        gpu_memory_usage = []
        for line in output.strip().split("\n"):
            index, memory_used = line.split(", ")
            gpu_memory_usage.append((int(index), int(memory_used)))

        return gpu_memory_usage
    except Exception as e:
        print(e)
        return []


def get_least_used_gpus(n):
    """Returns the indices of 'n' GPUs with the least memory usage."""
    gpu_memory_usage = get_gpus_memory_usage()

    # Sort GPUs based on memory usage
    sorted_gpus = sorted(gpu_memory_usage, key=lambda x: x[1])

    # Get the first 'n' GPUs
    return [gpu[0] for gpu in sorted_gpus[:n]]

# Example: Get the indices of the 3 GPUs with the least memory usage

if __name__ == "__main__":

    # Define the base directory
    base_directory = Path('./')

    # write reboot script if not exists
    reboot_script_path = base_directory / "reboot.py"
    if not reboot_script_path.exists():
        with open(reboot_script_path, 'w') as file:
            file.write(script_content)
            
    while True:
        time.sleep(1)
        # Iterate over all folders in the base directory
        for folder in base_directory.iterdir():
            try:
                if folder.is_dir():
                    docker_compose_path = folder / 'docker-compose.yml'
                    reboot_script_path = folder / 'assign'

                    # Check if the docker-compose file exists
                    if docker_compose_path.exists():
                        # Check if the file is more than 0 bytes
                        if reboot_script_path.exists() and reboot_script_path.stat().st_size > 0:
                            assign = 0
                            try:   
                                with open(reboot_script_path, 'r') as file:
                                    assign = int(file.readline())
                                with open(reboot_script_path, 'w') as file:
                                    pass
                            except Exception as err:
                                pass
                            newstr = ",".join(
                                [str(i) for i in get_least_used_gpus(assign)])
                            print("assigning gpu {} to: {}".format(newstr, folder.name))
                            # Read the docker-compose.yml file
                            with open(docker_compose_path, 'r') as file:
                                docker_compose = yaml.load(file)

                            file_modified = False
                            # Check if the 'services' section is in the file
                            if 'services' in docker_compose:
                                for service in docker_compose['services']:
                                    # Modify the environment variable
                                    env = docker_compose['services'][service].setdefault(
                                        'environment', [])
                                    if  len(newstr)>0:
                                        new_env = ['NVIDIA_VISIBLE_DEVICES={}'.format(newstr)]
                                    else:
                                        new_env = ['NVIDIA_VISIBLE_DEVICES=none']
                                    for each in env:
                                        if not each.find('NVIDIA_VISIBLE_DEVICES')>-1 :
                                            new_env.append(each)
                                        file_modified = True
                                    docker_compose['services'][service]['environment']=new_env
                                    print( docker_compose['services'][service]['environment'])
                            # print docker_compose yaml
                            
                            # Write the modified docker-compose file back and run 'docker compose up -d'
                            if True:
                                with open(docker_compose_path, 'w') as file:
                                    yaml.dump(docker_compose, file,
                                                default_flow_style=False)

                                # Run 'docker compose up -d' in the folder
                                subprocess.run(
                                    ['docker','compose', 'up', '-d'], cwd=str(folder))
            except Exception as err:
                pass
                
