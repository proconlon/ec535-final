# Setting up the BeagleBone
These are the details for running the program on the beaglebone with all the tools we added.


These 6 files must be placed in a dir on BeagleBone to run all aspects of the program.

- `bbb_logger_arm` - ran as `./bbb_logger_arm <ip of opcua server>`
- `config.txt`
- `capture` (0 or 1)
- `predictive_maintain.py`
- `upload.py` - with S3 credentials for AWS upload
- `ip_address` - the IP address of the OPC-UA server

Running the bbb logger creates two folders: `logs` and `train` for LF and HF data respectively. The logger also creates a `live_data` file that is constantly updated with each read for live data. You can monitor in a basic way with:
```sh
watch -n0.1 cat live_data
```

## Config

- Use the image and boot into it [am335x-11-7-2023-09-02-4gb-microsd-iot.img.xz](https://www.beagleboard.org/distros/am335x-11-7-2023-09-02-4gb-microsd-iot).  
- **eth0**: built-in port-- connect to WAN/DHCP for internet access
- **eth1**: via USB-Ethernet dongle to reach OPC-UA data simulator (running on a laptop)
- Edit `/etc/dhcpcd.conf` to give **eth1** a static IP and **eth0** with DHCP
- Create 2 systemd units (specified in `system_setup.md`) to run the logger and the ML model. 
- Create the cron job for the bufferred upload script.
- Install and configure tailscale as exit node:
```sh
sudo tailscale up \
  --advertise-exit-node \
  --advertise-routes=192.168.50.0/24 # subnet that OPC-UA server is on
```

## Cross compiling
- The main compiliation dependency is [github.com/open62541/open62541](https://github.com/open62541/open62541.git), which you need to download and build for Arm in order to compile.
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
