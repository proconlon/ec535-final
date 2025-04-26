CC = gcc
CFLAGS = -O2 -std=c11
LDFLAGS = -lopen62541 # for open62541-- opcua

TARGET = bbb_logger
SRC = main.c opc.c
OBJ = $(SRC:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJ) $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) $(TARGET)
