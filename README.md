# dckr_song_upload
This docker image is used to upload to ICGC using SONG client

## How to run
In a terminal:
```bash
docker pull quay.io/baminou/dckr_song_upload
docker run -e ACCESSTOKEN -v $(pwd):/app quay.io/baminou/dckr_song_upload upload -p /app/payload.json -s {STUDY_ID} -u {SONG_HOST} -o /app/manifest.txt -j /app/manifest.json
```
