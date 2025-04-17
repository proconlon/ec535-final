# EC535 Final

James Conlon \
conlon@bu.edu

Animisha Sharanappa \
anics@bu.edu

# cross Compile instructions

ensure you have all of these packages installed:
```sh
arm-linux-gnueabihf-binutils \
arm-linux-gnueabihf-gcc \
arm-linux-gnueabihf-gcc-c++ \
arm-linux-gnueabihf-glibc \
cmake \
make \
gcc
```

cd into collector/ and clone the open62541 repo (for OPCUA)
```sh
git clone https://github.com/open62541/open62541.git
cd open62541
```

- ensure toolchain-armhf.cmake is present in collector folder (already part of repo), just ensure it has correct paths to the folder.

create a build directory for beaglebone: armhf and  then configure cmake
- run from the collector folder
```sh
mkdir open62541_build_armhf
cd open62541_build_armhf

INSTALL_PATH="/home/james/open62541_armhf_install"
cmake ../open62541 \
    -DCMAKE_TOOLCHAIN_FILE=../toolchain-armhf.cmake \
    -DCMAKE_INSTALL_PREFIX=${INSTALL_PATH} \
    -DBUILD_SHARED_LIBS=OFF \
    -DUA_NAMESPACE_ZERO=FULL \
    -DCMAKE_BUILD_TYPE=MinSizeRel


make -j$(nproc)
make install

cd ..
```

Now the open62541 library is built and installed in the INSTALL_PATH.

If you are building open62541 for a different arch, create new toolchain for it

next, we statically compile the collector itself. note the install path isnt in the project dir but in my home folder. put it wherever.
```sh
INSTALL_PATH="/home/james/open62541_armhf_install"

arm-linux-gnueabihf-gcc \
    -march=armv7-a -mtune=cortex-a8 -mfpu=neon -mfloat-abi=hard \
    -I${INSTALL_PATH}/include \
    -L${INSTALL_PATH}/lib \
    -o data_collector_arm_static data_collector.c \
    -static \
    -lopen62541 \
    -lm -lpthread -lrt

```


# References

- [Logging on Embedded Devices](https://interrupt.memfault.com/blog/device-logging)