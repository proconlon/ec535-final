#include "opc.h"
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>
#include <errno.h>
#include <fcntl.h>

// config.txt stores each value on a new line
typedef struct {
    int hiRateHz;       // polling rate (Hz)
    int loRateHz;       // logging rate (Hz)
    int maxFileKB;      // max log file size before rotation
    int captureSeconds; // not used, currently u manually turn off the capture flag
    int captureEnabled; // also unused at present
} Config;

// volatile=signal safe
static volatile sig_atomic_t g_keepRunning = 1;

// Read five ints from text file (one per line)
int read_config(const char *path, Config *cfg) {
    FILE *f = fopen(path, "r"); 
    if (!f) return -1;
    if (fscanf(f, "%d\n%d\n%d\n%d\n%d", &cfg->hiRateHz, &cfg->loRateHz, &cfg->maxFileKB, &cfg->captureSeconds, &cfg->captureEnabled) != 5) {
        // error reading config
        fclose(f); 
        return -2;
    }
    fclose(f); 
    return 0; // no err
}

// signal for SIGINT/SIGTERM
void on_term(int sig) { 
    (void)sig; g_keepRunning = 0;
}

// open a NEW file with timestamp prefix
static FILE* rotate_file(const char *dir, const char *prefix) {
    char fname[128];
    // name as logs/log_timestamp.csv or train/train_timestamp.csv
    snprintf(fname, sizeof(fname), "%s/%s_%llu.csv", dir, prefix, (unsigned long long)time(NULL));
    return fopen(fname, "w");
}

int main(int argc, char **argv) {
    if (argc < 2) { 
        fprintf(stderr, "Usage: %s <server-ip>\n", argv[0]);
        return 1; 
    }


    // Load config.txt
    Config cfg;
    if (read_config("config.txt", &cfg) < 0) {
        printf("Failed to read config.txt\n"); return 1;
    }
    int decimateN = cfg.hiRateHz / cfg.loRateHz;
    printf("cfg loaded: hiRateHz=%d loRateHz=%d maxFileKB=%d\n", cfg.hiRateHz, cfg.loRateHz, cfg.maxFileKB);


    // set up signal handlers
    signal(SIGINT, on_term);
    signal(SIGTERM, on_term);
    system("mkdir -p logs train");


    // set up for watchability
    // use watch -n0.2 cat live_data
    FILE *lf = fopen("live_data", "w");
    if (lf) fclose(lf);


    // set up opcua client
    char url[256];
    snprintf(url, sizeof(url), "opc.tcp://%s:4840/freeopcua/server/", argv[1]);
    UA_Client *client = opcua_connect(url);
    if (!client) { 
        printf("[ERROR] opcua_connect failed\n"); 
        return 1; 
    }

    // log file rotation fp
    FILE *log_fp = rotate_file("logs", "log");
    if (!log_fp) { 
        perror("fopen log"); 
        return 1; 
    }


    // ml train file fp
    FILE *train_fp = NULL;
    int prevCap = 0; // previous HF capture state (0=off, 1=on)
    unsigned long long tick = 0;


    // main loop
    while (g_keepRunning) {
        // read capture config file
        int cap = 0;
        FILE *capf = fopen("capture", "r");
        if (capf) { 
            fscanf(capf, "%d", &cap); 
            fclose(capf); 
        
        
        }
        // On change, rotate train file
        if (cap && !prevCap) { // start capture
            train_fp = rotate_file("train", "train");
            if (!train_fp) {
                perror("fopen train");
            }
            printf("Started train capture, writing to train folder.\n");
        } else if (!cap && prevCap) { // stop capture
            if (train_fp) {
                fclose(train_fp);
            }
            train_fp = NULL;
            printf("Stopped train capture\n");
        }
        prevCap = cap; // update previous capture state

        // Read data from opcua server
        LogRow row;
        if (!opcua_read_row(client, &row)) {
            continue;

        }

        // DATA READ SUCCESS HERE
        
        // live data write for watch current data
        FILE *lf = fopen("live_data", "w");
        if (lf) { // TODO: make formatting better and not just clone of csv
            fprintf(lf, "%llu,%.2f,%.2f,%.2f,%.2f,%s,%d\n",
                row.ts_us, row.melt_temp,
                row.inj_press, row.vib_amp,
                row.vib_freq, row.stage, row.failure_label);
            fclose(lf);
        }

        // Low-rate logging always always goes to log_fp
        if (tick % decimateN == 0) {
            fprintf(log_fp, "%llu,%.2f,%.2f,%.2f,%.2f,%s,%u\n",
                    row.ts_us, row.melt_temp, row.inj_press,
                    row.vib_amp, row.vib_freq, row.stage, row.failure_label);
            fflush(log_fp);
            long pos = ftell(log_fp);
            if (pos/1024 >= cfg.maxFileKB) {
                fclose(log_fp);
                log_fp = rotate_file("logs", "log");
                printf("Rotated LOG file as size reached %dKB\n", cfg.maxFileKB);
            }
        }
        // High-rate logging WHEN CAPTURING goes to train_fp
        if (cap && train_fp) {
            fprintf(train_fp, "%llu,%.2f,%.2f,%.2f,%.2f,%s,%u\n",
                    row.ts_us, row.melt_temp, row.inj_press,
                    row.vib_amp, row.vib_freq, row.stage, row.failure_label);
            fflush(train_fp);
        }

        tick++;
        usleep(1000000 / cfg.hiRateHz); // sleep for hiRateHz
    }

    // cleanup
    fclose(log_fp);
    if (train_fp) fclose(train_fp);
    opcua_disconnect(client);
    return 0;
}
