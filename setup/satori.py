import subprocess as sp
import shlex
import os
import time
import psutil
import statistics
from scipy.stats.mstats import gmean
from skopt import gp_minimize
import signal
FNULL = open(os.devnull, 'w')

##Set time limit for the Bayesian Optimizer
def signal_handler(signum, frame):
    raise Exception("Total BO Engine Timeout Reached")

##Start the applications and return the pid
def start_jobs():
     colocated_job_command=['parsecmgmt -a run -p '+applications[j]+' -i '+dataset for j in range(len(applications))]
     for job in colocated_job_command:
          process=sp.Popen(shlex.split(job), shell=False)
     time.sleep(time_lag)
     pid_list=[]
     for job in colocated_job_command:
          pid=sp.run(shlex.split('pgrep '+applications[colocated_job_command.index(job)]), stdout=sp.PIPE)
          pid_list.append(pid.stdout)
     pid_list=[int(i) for i in pid_list]
     return pid_list

#Collect the IPS through perf and calculate throughput and fairness
def get_metrics():
    global equalization_period_counter
    global prioritization_period_counter
    j=0
    while j<len(pid_list) and j<len(applications):                                                                         ## collecting ips of applications
         sp.check_output(shlex.split('bash ips_collector.sh '+str(pid_list[j])+' '+str(applications[j]+'_ips.txt'))) 
         j+=1
    th_list=[]                                                                                                             ## calculate throughput 
    for app in applications: 
        f_read=open(app+"_ips.txt")
        last_line=f_read.readlines()[-(4)]
        f_read.close()
        split_line=last_line.split()
        th_list.append(int(split_line[0].replace(',','')))
    speedup_list=[th_list[k]/isolated_ips[k] for k in range(len(isolated_ips))]                                           ## calculate fairness
    fairness_list.append(1/(1+(statistics.stdev(speedup_list)/statistics.mean(speedup_list))**2))
    throughput_list.append(gmean(speedup_list))
    if time.time()-equalization_period_counter>=time_equalization:
        equalization_period_counter=time.time()
        equalization_period_marker_list.append(1)
    else:
        equalization_period_marker_list.append(0)

    if time.time()-prioritization_period_counter>=time_prioritization:
        prioritization_period_counter=time.time()
        prioritization_period_marker_list.append(1)
    else:
        prioritization_period_marker_list.append(0)
    
    if len(equalization_period_marker_list)==1:
       equalization_period_marker_list[0]=1
       prioritization_period_marker_list[0]=1


# Generate allocations configurations starting with application 'a' given 'u' units of resource 'r'
def gen_configs_recursively(u, r, a):
    if (a == NUM_APPS-1):
        return None
    else:
        ret = []
        for i in range(1, NUM_UNITS[r]-u+1-NUM_APPS+a+1):
            confs = gen_configs_recursively(u+i, r, a+1)
            if not confs:
                ret.append([i])
            else:
                for c in confs:
                    ret.append([i])
                    for j in c:
                        ret[-1].append(j)
        return ret


##Generates list of all possible partitioning configurations
# Example of a configuration in this scenario: [c11, c12, c21, c22, c31, c33] = [1, 2, 4, 4, 5, 3]
# c11 = 1 = App 1's allocation of resource 1
# c12 = 2 = App 2's allocation of resource 1
# c13 = 10 - 1 - 2 = 7 = App 3's allocation of resource 1 (inferred but not explicitly shown)
# c21 = 4 = App 1's allocation of resource 2
# c22 = 4 = App 2's allocation of resource 2
# c33 = 11 - 4 - 4 = 3 = App 3's allocation of resource 2 (inferred but not explicitly shown)
# c31 = 5 = App 1's allocation of resource 3
# c32 = 5 = App 2's allocation of resource 3
# c33 = 10 - 5 - 3 = 2 = App 3's allocation of resource 3 (inferred but not explicitly shown)
def gen_configs():
    global CONFIGS_LIST
    for r in range(NUM_RESOURCES):
        if not CONFIGS_LIST:
            CONFIGS_LIST = gen_configs_recursively(0, r, 0)
        else:
            CONFIGS_LIST = [x + y for x in CONFIGS_LIST for y in gen_configs_recursively(0, r, 0)]

#get the allocation of all the resources for each of the applications
def get_allocation(x):
    sampled_config=CONFIGS_LIST[x]
    core_list=[]
    llc_list=[]
    mba_list=[]
    i=0
    j=0
    for j in range(len(applications)-1):
        core_list.append(sampled_config[i])
        i+=1
    core_list.append(NUM_UNITS[0]-sum(core_list))
    j=0
    for j in range(len(applications)-1):
        llc_list.append(sampled_config[i])
        i+=1
    llc_list.append(NUM_UNITS[1]-sum(llc_list))
    j=0
    for j in range(len(applications)-1):
        mba_list.append(sampled_config[i])
        i+=1
    mba_list.append(NUM_UNITS[2]-sum(mba_list))
    core_allocation_list=[]
    mba_allocation_list=[]
    llc_allocation_list=[]
    j=0
    i=0
    for j in range(len(applications)):
        if core_list[j]!=1:
            s=str(i)+"-"+str(i+core_list[j]-1)+","+str(i+NUM_UNITS[0])+"-"+str(i+core_list[j]+NUM_UNITS[0]-1)
        else:
             s=str(i)+","+str(i+NUM_UNITS[0])
        core_allocation_list.append(s)
        i+=core_list[j]
    j=0
    i=NUM_UNITS[1]-1
    for j in range(len(applications)):
        ini_list=[0 for k in range(NUM_UNITS[1])]
        count=llc_list[j]
        while count >0:
            ini_list[i]=1
            i-=1
            count-=1
        llc_allocation_list.append(hex(int(''.join([str(item) for item in ini_list]), 2)))
    j=0
    for j in range(len(applications)):
        s=str(mba_list[j]*10)
        mba_allocation_list.append(s)
    return core_allocation_list, llc_allocation_list, mba_allocation_list

##Use taskset, and intel CAT and MBA tools to partition resources among co-running applications
def perform_resource_partitioning(core_allocation_list,llc_allocation_list,mba_allocation_list):
    
    for j in range(NUM_APPS):
        taskset_cmnd = TASKSET + core_allocation_list[j] + " " + str(pid_list[j])
        cos_cat_set1 = COS_CAT_SET1 % (str(j+1), llc_allocation_list[j])
        cos_cat_set2 = COS_CAT_SET2 % (str(j+1), core_allocation_list[j])
        cos_mBG_set1 = COS_MBG_SET1 % (str(j+1), mba_allocation_list[j])
        cos_mBG_set2 = COS_MBG_SET2 % (str(j+1), core_allocation_list[j])
        
        sp.check_output(shlex.split(taskset_cmnd), stderr=FNULL)
        sp.check_output(shlex.split(cos_cat_set1), stderr=FNULL)
        sp.check_output(shlex.split(cos_cat_set2), stderr=FNULL)
        sp.check_output(shlex.split(cos_mBG_set1), stderr=FNULL)
        sp.check_output(shlex.split(cos_mBG_set2), stderr=FNULL)

##Get the throughput and fairness weights through dynamic prioritization of conflicting goals
def get_weights():
    if len(WT_list)==0:
        W_T=0.5
        W_F=0.5
        WT_list.append(W_T)
        WF_list.append(W_F)
        return W_T, W_F
    else:
        global start_time
        equalization_index=max([i for i in range(len(equalization_period_marker_list)) if equalization_period_marker_list[i]==1])
        prioritization_index=max([i for i in range(len(prioritization_period_marker_list)) if prioritization_period_marker_list[i]==1])
        change_fairness=(fairness_list[len(fairness_list)-1]-fairness_list[prioritization_index])/fairness_list[prioritization_index]
        change_throughput=(throughput_list[len(throughput_list)-1]-throughput_list[prioritization_index])/throughput_list[prioritization_index]
        if change_fairness<=0 and change_throughput<=0:
            W_TP=0.5
            W_FP=0.5
        elif change_fairness<0 and change_throughput>0:
            W_TP=0.25
            W_FP=0.75
        elif change_fairness>0 and change_throughput<0:
            W_TP=0.75
            W_FP=0.25
        else:
            W_TP=0.25+0.5*(change_fairness/(change_throughput+change_fairness))
            W_FP=0.25+0.5*(change_throughput/(change_throughput+change_fairness))
        W_TE=1-statistics.mean(WT_list[equalization_index:])
        W_FE=1-statistics.mean(WF_list[equalization_index:])
        te=(time.time()-start_time)%time_equalization
        W_T=(te/time_equalization)*W_TE + (1-(te/time_equalization))*W_TP
        W_F=(te/time_equalization)*W_FE + (1-(te/time_equalization))*W_FP
        return W_T, W_F

##Calculate the objective function value at sampled configurations 
def objective(x):
    core_allocation_list, llc_allocation_list, mba_allocation_list=get_allocation(x[0])
    perform_resource_partitioning(core_allocation_list, llc_allocation_list, mba_allocation_list)
    time.sleep(time_sampling)
    get_metrics()
    W_T, W_F=get_weights()
    return -1*(W_T*throughput_list[len(throughput_list)-1]+W_F*fairness_list[len(fairness_list)-1])


def start_bo_engine():
     get_metrics()
     time.sleep(time_sampling)
     res=gp_minimize(objective,
                     [(0, len(CONFIGS_LIST)-1)],
                     n_calls=1000,
                     n_random_starts=5,
                     acq_func='EI',
                     random_state=1234)

if __name__ == "__main__":
     time_lag=5 ## initial time before Bayesian Optimizer starts 
     time_sampling=0.1 ##Sampling time
     time_total=1000 ##Total time for Bayesian Optimizer to work
     time_prioritization=10 ##Prioritization Period
     time_equalization=25 ##Equalization Period
     applications=['freqmine', 'streamcluster', 'fluidanimate'] ##Applications to co-locate
     isolated_ips=[60435286, 40209642, 97545245]  ##Isolated IPS values of the applications (pre-calculated)
     dataset='native' ##Representative input dataset for the applications 
     NUM_APPS=len(applications)
     NUM_RESOURCES = 3 ##Number of resources to partition: cores, LLC, and Mem. B/W.
     NUM_UNITS  = [10, 11, 10] ## Number partitions of each of the resources: 10 cores (with hyperthreading), 11 cache ways, memory bandwidth partitioned into 10 parts
     CONFIGS_LIST  = []
     throughput_list=[]
     fairness_list=[]
     equalization_period_marker_list=[]
     prioritization_period_marker_list=[]
     WT_list=[]
     WF_list=[]
     TASKSET       = "sudo taskset -acp "
     COS_CAT_SET1  = "sudo pqos -e \"llc:%s=%s\""
     COS_CAT_SET2  = "sudo pqos -a \"llc:%s=%s\""
     COS_MBG_SET1  = "sudo pqos -e \"mba:%s=%s\""
     COS_MBG_SET2  = "sudo pqos -a \"core:%s=%s\""
     COS_RESET     = "sudo pqos -R"

     gen_configs()
     pid_list=start_jobs()
     signal.signal(signal.SIGALRM, signal_handler)
     equalization_period_counter=time.time()
     prioritization_period_counter=time.time()
     start_time=time.time()
     signal.alarm(time_total)  
     try:
        start_bo_engine()
     except Exception:
        print("Total BO Engine Timeout Reached")
 

































