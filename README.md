# SATORI : Efficient and Fair Resource Partitioning by Sacrificing Short-Term Benefits for Long-Term Gains

If you use SATORI in your scientific article, please cite our ISCA 2021 paper: </br>
*Rohan Basu Roy, Tirthak Patel, and Devesh Tiwari. "SATORI : Efficient and Fair Resource Partitioning by Sacrificing Short-Term Benefits for Long-Term Gains." In ACM/IEEE International Symposium on Computer Architecture (ISCA), 2021.*

## Dependencies

SATORI is tested on a  Ubuntu Server 20.04 LTS using Python3.6. Please install the following library depencies for running SATORI. </br>

```
pip3 install scipy  
pip3 install scikit-optimize  
apt-get install linux-tools-common linux-tools-generic linux-tools-`uname -r` 

```
It uses the Linux utility *perf* for Intructions per second (IPS) monitoring of the individual applications. Ensure that *Intel CAT* (for last level cache partitioning), *MBA* (for memory bandwidth partitioning), and *taskset* (for compute core partitioning) tools are supported and active in your system.</br>


## Run SATORI

In the script *satori.py*, input the following in the main function:</br>
```
applications:

```
Give the name of the applications you want to co-locate. We evaluated SATORI on [Parsec benchmark suite](https://parsec.cs.princeton.edu/parsec3-doc.htm). </br>
```
isolated_ips:

```
Run the applications without co-location once and input their mean IPS. </br>
```
NUM_UNITS:

```
Input the number of partitioning units of compute cores, last level cache ways and memeory bandwidth in your system. </br>

According to your choice, you can also set the different time parameters: *time_prioritization* (prioritization time period), *time_equalization* (equalization time period), *time_sampling* (sampling time between two evaluations), *time_total* (total time to carry out the optimization), and *time_lag* (time between the launch of the applications and the start of the optimization). You can also set the variable *dataset* to your choice of input data. You can also set the different parameters of the Bayesian Optimizer (BO) engine. </br>

To run use: ``` sudo python3 satori.py ``` </br>

The script *ips_collector.sh* is used to collect the IPS of the co-located applications.
 



