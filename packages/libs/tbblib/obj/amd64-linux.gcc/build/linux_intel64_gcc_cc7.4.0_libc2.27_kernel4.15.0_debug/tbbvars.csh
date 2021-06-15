#!/bin/csh
setenv TBB30_INSTALL_DIR "/home/rohan/uforea/parsec-3.0/pkgs/libs/tbblib/obj/amd64-linux.gcc" #
setenv tbb_bin "/home/rohan/uforea/parsec-3.0/pkgs/libs/tbblib/obj/amd64-linux.gcc/build/linux_intel64_gcc_cc7.4.0_libc2.27_kernel4.15.0_debug" #
if (! $?CPATH) then #
    setenv CPATH "${TBB30_INSTALL_DIR}/include" #
else #
    setenv CPATH "${TBB30_INSTALL_DIR}/include:$CPATH" #
endif #
if (! $?LIBRARY_PATH) then #
    setenv LIBRARY_PATH "${tbb_bin}" #
else #
    setenv LIBRARY_PATH "${tbb_bin}:$LIBRARY_PATH" #
endif #
if (! $?LD_LIBRARY_PATH) then #
    setenv LD_LIBRARY_PATH "${tbb_bin}" #
else #
    setenv LD_LIBRARY_PATH "${tbb_bin}:$LD_LIBRARY_PATH" #
endif #
 #
