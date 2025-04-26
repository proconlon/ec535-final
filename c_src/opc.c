#include "opc.h"
#include <open62541/client.h>
#include <open62541/client_config_default.h>
#include <open62541/client_highlevel.h>
#include <string.h>
#include <time.h>
#include <stdio.h>

// hard code the NodeId info (use data_simulator/get_ns.py) to get the ns, id for the data sim
static const struct {
    UA_UInt16 ns; //namespace 
    UA_UInt32 id; // node id within namespace
} nodeInfo[6] = {
    {2, 2},  // MeltTemp
    {2, 3},  // InjectionPressure
    {2, 4},  // VibrationAmplitude
    {2, 5},  // VibrationFrequency
    {2, 6},  // Stage
    {2, 7}   // Timestamp
};

static UA_NodeId g_nodeIds[6];
static const char *NODES[6] = { // names for debug lines(not saved to csv)
    "MeltTemp",
    "InjectionPressure",
    "VibrationAmplitude",
    "VibrationFrequency",
    "Stage",
    "Timestamp"
};

// connect to server and init nodes
UA_Client* opcua_connect(const char* endpoint) {
    UA_Client *client = UA_Client_new();
    UA_ClientConfig_setDefault(UA_Client_getConfig(client));
    if (UA_Client_connect(client, endpoint) != UA_STATUSCODE_GOOD) {
        UA_Client_delete(client);
        return NULL;
    }
    printf("Connected to %s\n", endpoint);

    // have to init each Node then you can return UA_Client
    for (int i = 0; i < 6; i++) {
        g_nodeIds[i] = UA_NODEID_NUMERIC(nodeInfo[i].ns, nodeInfo[i].id);
        printf("Init %s -> ns=%u;i=%u\n", NODES[i], g_nodeIds[i].namespaceIndex, g_nodeIds[i].identifier.numeric);
    }
    return client;
}

void opcua_disconnect(UA_Client* client) {
    if (!client) return;
    UA_Client_disconnect(client);
    UA_Client_delete(client);
}

int opcua_read_row(UA_Client* client, LogRow *out) {
    UA_Variant value;

    // read all 6 values on each read
    for (int i = 0; i < 6; i++) {
        UA_Variant_init(&value); // init the variant
        UA_StatusCode s = UA_Client_readValueAttribute(client, g_nodeIds[i], &value); // fetch the value
        if (s != UA_STATUSCODE_GOOD) {
            printf("[ERROR] read %s failed: %s\n", NODES[i], UA_StatusCode_name(s));
            UA_Variant_clear(&value); // clear the value
            continue; // bad read, can skip to next though i doubt that will be any good either =/
        }

        // set the value in the struct 
        // more work to save the string
        if (i == 0) {
            out->melt_temp = *(UA_Double*)value.data;
        }
        else if (i == 1) {
            out->inj_press = *(UA_Double*)value.data;
        }
        else if (i == 2) {
            out->vib_amp = *(UA_Double*)value.data;
        }
        else if (i == 3) {
            out->vib_freq = *(UA_Double*)value.data;
        }
        else if (i == 4) { // stage
            UA_String *str = (UA_String*)value.data;
            size_t len = str->length < sizeof(out->stage)-1 ? str->length: sizeof(out->stage)-1; // to be safe that we don't overflow
            memcpy(out->stage, str->data, len);
            out->stage[len] = '\0'; // null terminate
        }
        else { //timestamp
            if (UA_Variant_hasScalarType(&value, &UA_TYPES[UA_TYPES_DOUBLE])) {
                UA_Double secs = *(UA_Double*)value.data;
                out->ts_us = (unsigned long long)(secs * 1e6); // sec -> micros
            } 
        }
        UA_Variant_clear(&value);
    }

    // the failure label is defined here
    out->failure_label = 0; 
    // TODO: Parameterize the failure label here
    // it should just read the state from the opcua server when part replacement happens
    // part replacement == predictable failure

    return 1;
}
