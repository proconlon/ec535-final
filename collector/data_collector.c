#include <open62541/client.h>
#include <open62541/client_config_default.h>
#include <stdlib.h>
#include <stdio.h>
#include <signal.h>
#include <unistd.h>
#include <time.h>


void readAndPrint(UA_Client *client, const char *name) 
{
    UA_Variant value;
    UA_Variant_init(&value);

    char nodeIdStr[256];
    snprintf(nodeIdStr, sizeof(nodeIdStr), "ns=2;s=%s", name);
    UA_NodeId nodeId = UA_NODEID_STRING_ALLOC(2, name);
    UA_StatusCode status = UA_Client_readValueAttribute(client, nodeId, &value);

    if(status == UA_STATUSCODE_GOOD && UA_Variant_hasScalarType(&value, &UA_TYPES[UA_TYPES_DOUBLE])) 
        printf("%s: %.2f\n", name, *(UA_Double *) value.data);
    
    else if(status == UA_STATUSCODE_GOOD && UA_Variant_hasScalarType(&value, &UA_TYPES[UA_TYPES_INT32])) 
        printf("%s: %d\n", name, *(UA_Int32 *) value.data); 

    else 
        printf("Failed to read %s: %s\n", name, UA_StatusCode_name(status));

    UA_Variant_clear(&value);
    UA_NodeId_clear(&nodeId);
}

int main(int argc, char *argv[]) 
{
    if (argc < 2) {
        printf("Pass the ip addr as a parameter\nUsage: %s <server-ip>\n", argv[0]);
        return 1;
    }
    UA_Client *client = UA_Client_new();
    UA_ClientConfig_setDefault(UA_Client_getConfig(client));


    char endpointUrl[256];
    snprintf(endpointUrl, sizeof(endpointUrl), "opc.tcp://%s:4840/freeopcua/server/", argv[1]);
    //UA_StatusCode status = UA_Client_connect(client, "opc.tcp://localhost:4840/freeopcua/server/");
    UA_StatusCode status = UA_Client_connect(client, endpointUrl);
    if(status != UA_STATUSCODE_GOOD) 
    {
        UA_Client_delete(client);
        fprintf(stderr, "Failed to connect: %s\n", UA_StatusCode_name(status));
        return -1;
    }

    const char *variables[] = {
        "MeltTemp",
        "InjectionPressure",
        "VibrationAmplitude",
        "VibrationFrequency",
        "Stage"
    };

    while(true) 
    {
        printf("Reading at %ld ms:\n", time(NULL) * 1000);
        for(int i = 0; i < 5; ++i) 
            readAndPrint(client, variables[i]);

        printf("\n");
        usleep(100000); 
    }

    UA_Client_disconnect(client);
    UA_Client_delete(client);
    return 0;
}
