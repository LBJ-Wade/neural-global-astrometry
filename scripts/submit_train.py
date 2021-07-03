import os
import numpy as np

batch = """#!/bin/bash

#SBATCH --job-name=train
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=32GB
#SBATCH --time=23:59:00
#SBATCH --gres=gpu:1
##SBATCH --mail-type=begin
#SBATCH --mail-type=end
#SBATCH --mail-user=siddharthmishra19@gmail.com

source ~/.bashrc
conda activate sbi-fermi
cd /scratch/sm8383/sbi-astrometry/
"""

##########################
# Explore configurations #
##########################

batch_size_list = [256]
activations = ["relu"]
kernel_size_list = [4]
n_neighbours_list = [8]
laplacian_types = ["combinatorial"]
conv_types = ["chebconv"]
conv_source_list = ["deepsphere"]
sigma_noise_list = np.linspace(0.0002, 0.005, 10)

for n_neighbours in n_neighbours_list:
    for batch_size in batch_size_list:
        for activation in activations:
            for kernel_size in kernel_size_list:
                for laplacian_type in laplacian_types:
                    for conv_type in conv_types:
                        for conv_source in conv_source_list:
                            for sigma_noise in sigma_noise_list:
                                batchn = batch + "\n"
                                batchn += "python -u train.py --sample train --name vary_noise --batch_size {} --activation {} --kernel_size {} --laplacian_type {} --conv_type {} --n_neighbours {} --conv_source {} --sigma_noise {}".format(batch_size, activation, kernel_size, laplacian_type, conv_type, n_neighbours, conv_source, sigma_noise)
                                fname = "batch/submit.batch"
                                f = open(fname, "w")
                                f.write(batchn)
                                f.close()
                                os.system("chmod +x " + fname)
                                os.system("sbatch " + fname)