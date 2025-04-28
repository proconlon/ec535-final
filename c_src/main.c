#include "opc.h"
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>
#include <errno.h>
#include <fcntl.h>
#include <dirent.h>
#include <sys/stat.h>
#include <string.h>
#include <limits.h>

// config.txt stores each value on a new line
typedef struct {
    int hiRateHz;       // polling rate (Hz)
    int loRateHz;       // logging rate (Hz)
    int maxLogFileKB;   // max log file size before rotation (right now, no cap on train files)
    int maxLogDirKB;
    int maxTrainDirKB;
    int captureSeconds; // not used, currently u manually turn off the capture flag
    int captureEnabled; // also unused at present
} Config;

// volatile=signal safe
static volatile sig_atomic_t g_keepRunning = 1;

static int dir_usage_kb(const char *dir);

// Read five ints from text file (one per line)
int read_config(const char *path, Config *cfg) {
    FILE *f = fopen(path, "r"); 
    if (!f) return -1;
    if (fscanf(f, "%d\n%d\n%d\n%d\n%d\n%d\n%d", &cfg->hiRateHz, &cfg->loRateHz, &cfg->maxLogFileKB, &cfg->maxLogDirKB, &cfg->maxTrainDirKB, &cfg->captureSeconds, &cfg->captureEnabled) != 7) {
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
    printf("cfg loaded: hiRateHz=%d loRateHz=%d maxLogFileKB=%d maxLogDirKB=%d maxTrainDirKB=%d\n", cfg.hiRateHz, cfg.loRateHz, cfg.maxLogFileKB, cfg.maxLogDirKB, cfg.maxTrainDirKB);


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
        // read primary config file
        if (read_config("config.txt", &cfg) < 0) {
            printf("config.txt missing, ending program.\n");
            return -1;
        } else {
            // recalculate decimation in case rates changed
            decimateN = cfg.hiRateHz / cfg.loRateHz;
        }

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

            fprintf(lf, "\nConfig: \n  HiHz\t\t%d\n  LoHz\t\t%d\n  maxLogFileKB\t%d\n  maxLogDirKB\t%d\n  maxTrainDirKB\t%d\n  CaptureSec\t%d (unused)\n  CaptureEnable\t%d (unused)\n", 
                cfg.hiRateHz, cfg.loRateHz, cfg.maxLogFileKB, cfg.maxLogDirKB, 
                cfg.maxTrainDirKB, cfg.captureSeconds, cfg.captureEnabled);
            fprintf(lf, "Capture file: %d\n", prevCap);

            // calculate dir sizes
            int totalLogKB = dir_usage_kb("logs");
            int totalTrainKB = dir_usage_kb("train");

            fprintf(lf,"Total Log dir usage:   %dKB / %dKB (%d%% of cap)\n", totalLogKB, cfg.maxLogDirKB, cfg.maxLogDirKB ? (totalLogKB * 100 / cfg.maxLogDirKB): 0);
            fprintf(lf,"Total Train dir usage: %dKB / %dKB (%d%% of cap)\n", totalTrainKB, cfg.maxTrainDirKB, cfg.maxTrainDirKB ? (totalTrainKB * 100 / cfg.maxTrainDirKB): 0);

            fprintf(lf, "Bytes/KBytes per second LF: %dB/s, %.2fKB/s\n", 
                cfg.loRateHz * sizeof(LogRow),
                (float)(cfg.loRateHz * sizeof(LogRow)) / 1024.0);
            fprintf(lf, "Bytes/KBytes per second HF: %dB/s, %.2fKB/s\n", 
                cfg.hiRateHz * sizeof(LogRow),
                (float)(cfg.hiRateHz * sizeof(LogRow)) / 1024.0);

            fprintf(lf, "Storage full in ...\n");
            
            fclose(lf);
        }

        // Low-rate logging always always goes to log_fp
        if (tick % decimateN == 0) {
            fprintf(log_fp, "%llu,%.2f,%.2f,%.2f,%.2f,%s,%u\n",
                    row.ts_us, row.melt_temp, row.inj_press,
                    row.vib_amp, row.vib_freq, row.stage, row.failure_label);
            fflush(log_fp);
            long pos = ftell(log_fp);
            if (pos/1024 >= cfg.maxLogFileKB) {
                fclose(log_fp);
                log_fp = rotate_file("logs", "log");
                printf("Rotated LOG file as size reached %dKB\n", cfg.maxLogFileKB);
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

// returns in kb the total size of files in a dir 
static int dir_usage_kb(const char *dir) {
    DIR *dp = opendir(dir);
    if (!dp) return 0;

    struct dirent *de;
    struct stat st;
    char path[PATH_MAX];
    long long total_bytes = 0;

    while ((de = readdir(dp))) {
        if (strcmp(de->d_name, ".") == 0 || strcmp(de->d_name, "..") == 0)
            continue;
        snprintf(path, sizeof(path), "%s/%s", dir, de->d_name);
        if (stat(path, &st) == 0 && S_ISREG(st.st_mode)) {
            total_bytes += st.st_size;
        }
    }

    closedir(dp);
    return (int)((total_bytes + 1023) / 1024);
}
