# BeagleBone setup details

This is crontab for the upload script:
```
*/5 * * * * /usr/bin/python3 /home/debian/upload.py >> /home/debian/upload.log 2>&1
```

This is the systemd for the ML model which should be always running. (`predictive_maintain.service`)
```sh
[Unit]
Description=Predictive Maintenance Model and Notifier
After=network.target

[Service]
Type=simple
User=debian
WorkingDirectory=/home/debian
ExecStart=/usr/bin/python3 /home/debian/predictive_maintain.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

- Ensure that the BBB has one ethernet port to real ethernet and the other to the OPC-UA server. The actual `./bbb_logger <server ip>` is run with one arg as the ip address of the OPC-UA server.
So you can add to systemd with this. Then place a file `server_ip` in the same dir. (`bbb_logger.service`)
```sh
[Unit]
Description=BeagleBone Black Main Logger
After=network.target

[Service]
Type=simple
User=debian
WorkingDirectory=/home/debian
# Reads the OPC-UA server IP from server_ip and passes it in
ExecStart=/bin/sh -c '/home/debian/bbb_logger_arm $(cat /home/debian/ip_address)'
Restart=always
RestartSec=5
StandardOutput=append:/home/debian/bbb_logger.log
StandardError=append:/home/debian/bbb_logger.err

[Install]
WantedBy=multi-user.target
```

Then you can view logs like: `tail -f /home/debian/bbb_logger.log`

The home directory should look like this at minimum, with other files created automatically by the logger.
```sh
-rwxr-xr-x 1 debian debian 9989656 Apr 29 01:35 bbb_logger_arm
-rw-r--r-- 1 debian debian       2 Apr 29 01:16 capture
-rw-r--r-- 1 debian debian      26 Apr 29 01:38 config.txt
-rw-r--r-- 1 debian debian      12 Apr 29 00:33 ip_address
-rw-r--r-- 1 debian debian       2 Apr 29 01:40 email_notif.py
-rw-r--r-- 1 debian debian    1532 Apr 29 01:17 upload.py
```


Lastly, we installed tailscale on the BBB for remote access. You should configure as `exit node` and `subnet router` so that you can access the OPC-UA server on the second ethernet interface remotely. Thus the beagle bone becomes a powerful device for remote access.


