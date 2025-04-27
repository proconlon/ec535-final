# bbb ARM builder
CC = arm-linux-gnueabihf-gcc
CFLAGS = -O2 -std=c11
LDFLAGS = -lopen62541

CFLAGS += -Ilogger-arm/open62541_install/include
LDFLAGS += -Llogger-arm/open62541_install/lib -static

TARGET = bbb_logger_arm

SRC = ../c_src/main.c ../c_src/opc.c
OBJ = $(patsubst ../c_src/%.c, %.o, $(SRC))

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJ) $(LDFLAGS)

%.o: ../c_src/%.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) $(TARGET)
