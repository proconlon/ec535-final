// opc.h
#ifndef OPC_H
#define OPC_H

#include <open62541/client.h>

typedef struct {
    unsigned long long ts_us;
    double melt_temp;
    double inj_press;
    double vib_amp;
    double vib_freq;
    char   stage[32];
    unsigned char failure_label; // for ML TBD
} LogRow;

UA_Client* opcua_connect(const char* endpoint);
void opcua_disconnect(UA_Client* client);
int opcua_read_row(UA_Client* client, LogRow *out);

#endif // OPC_H
