These are the details for running the program on the beaglebone with all the tools we added.


# Config BeagleBone

These 4 files must be placed in a dir on BeagleBone to run all aspects of the program.

- `bbb_logger_arm` - ran as `./bbb_logger_arm <ip of opcua server>`
- `config.txt`
- `capture` (0 or 1)
- `monitor.py`
- `upload.py`

Running the bbb logger creates two folders: `logs` and `train` for LF and HF data respectively. The logger also creates a `live_data` file that is constantly updated with each read for live data. You can monitor in a basic way with:
```sh
watch -n0.2 cat live_data
```

# Setup BeagleBone

- setup details like how to get dual ethernet, base image, running the program, etc.

- [BeagleBone image used](https://www.beagleboard.org/distros/am335x-11-7-2023-09-02-4gb-microsd-iot)

- set up a cron job for the `upload.py` that will upload and delete bufferred data.


# Cross compiling
- The only compiliation dependency is [github.com/open62541/open62541](https://github.com/open62541/open62541.git), which you need to download and build for Arm in order to compile.
- We compile statically so only the final binary needs to be copied and not the open62541 library to the BeagleBone.

```sh
# make a Arm compile directory you can remove later
mkdir -p logger-arm/
cd logger-arm/

git clone https://github.com/open62541/open62541.git
cd open62541
mkdir build && cd build
cmake \
    -DCMAKE_C_COMPILER=arm-linux-gnueabihf-gcc \
    -DBUILD_SHARED_LIBS=OFF \
    -DCMAKE_INSTALL_PREFIX=../../open62541_install \
    ..
make
make install
cd ../../../
```

There is a separate Makefile for the cross compile. If you made the logger-arm folder in this dir, you can just run the following from the beaglebone folder:
```sh
make
```

This creates the `bbb_logger_arm` which you can copy over with scp to the beaglebone.

```sh
scp bbb_logger_arm USER@BEAGLEBONE_IP:/home/debian/

ssh USER@BEAGLEBONE_IP

# ensure a config.txt and capture file is present

./bbb_logger_arm <ip of opcua server> 
```
