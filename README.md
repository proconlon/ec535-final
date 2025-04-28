# EC535 Final

James Conlon \
conlon@bu.edu

Animisha Sharanappa \
anics@bu.edu

# Overview


# Config and Metrics

This project tracks a number of metrics for data and storage saving reasons. This is important as sometimes factory floor would have the beaglebone device segmented from the local network and on a Sim card, so it can't send unlimited data to the cloud.

Thus it should log at a much high frequency for ML training and log at a lower frequency for persistent cloud storage. This is also useful as large amounts of persisted data being stored on some cloud would be expensive, wasteful, and pointless to store.

- Logging at a high frequency is important for ML/Predictive Maintenance
- Logging at a low frequency is used for persistent cloud storage

The project includes a number of ways to live calculate and estime data, network, and storage usage and predict based on current data usage.

## Config file details

This is what you define in the `config.txt` that is placed alongside the `bbb_logger` binary.
```c
int hiRateHz;       // polling rate (Hz) (HF, for ML training)
int loRateHz;       // logging rate (Hz) (LF, for cloud storage)
int maxFileKB;      // max log file size before rotation
```

Since we don't want to continously store the Hi rate data, we introduced a file called `capture` that if set to `1` will store HF data at the frequency defined. If set to `0` it will only store LF data. 

```sh
echo 1 > capture
```

You can also live watch the currently read data and system static with the file `live_data`
```sh
watch -n0.2 cat live_data
```

## Metrics

Since each line in the csv represents one data point, we will average the size of a line and use for a number of calculations for storage.

- We use a cron job on a python script to upload stored data to cloud. Since we locally buffer data, the timing of the cron job doesn't really matter. (We set to 5 minutes). What does matter is the frequency of the LF data we store.
- We implemented a tool that estimates the daily/monthly network usage based on an inputted LF Hz rate and a sample of the csv data. 
- We do the same for HF data for ML. The intent is to train locally to save cloud costs as there would be a lot more data.
- Calculates low rate bytes/sec and high rate bytes/sec. 
- Calculates time to capacity estimates intil we fill the maxFileKB and an amount of storage on the SD card itself. Since data sent to the cloud is deleted from local, we just need this to ensure we don't fill the SD card and we don't generate more data than the latency of the upload.
- Thus we also calculate throughputs and such using a user estimated upload speed.
- Lots of data volume information.
- Also do what if calculations for the following:
    - If I want to capture HF data for X hours, how much data will it generate, and how long will it take to upload?
    - If you have X MB free on SD, how many hours of LF/HF data can you store?

# Predictive Maintenance

- Implements a locally run ML model on the HF data to predict machine simulated failures.
- It is key that it is locally run because we established that this would be too much data to send to cloud and relatively pointless to send 100Hz+ data to cloud. 
- So it is locally run and alerts the machine operator via email when a failure is predicted.
- The `capture` flag is for training the model, so that data is sent to cloud for training a model.
- Plan to implement alerts for low storage?



# References

## Predictive Maintenance

- [Deloitte - Asset Optimization: Predictive Maintenance](https://www2.deloitte.com/us/en/pages/operations/articles/predictive-maintenance-and-the-smart-factory.html)
- [AWS - What is Predictive Maintenance?](https://aws.amazon.com/what-is/predictive-maintenance/)

## Project

- [Logging on Embedded Devices](https://interrupt.memfault.com/blog/device-logging)