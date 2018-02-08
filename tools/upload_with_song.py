#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
from overture_song.model import ApiConfig, Manifest, ManifestEntry
from overture_song.client import Api, ManifestClient, StudyClient
from overture_song.tools import FileUploadClient
from overture_song.utils import write_object, setup_output_file_path
import subprocess
import requests


def create_manifest(api,analysis_id, files_dir):
    manifest = Manifest(analysis_id)
    for file_object in api.get_analysis_files(analysis_id):
        manifest_entry = ManifestEntry.create_manifest_entry(file_object)
        manifest_entry.fileName = os.path.join(files_dir,manifest_entry.fileName)
        manifest.add_entry(manifest_entry)
    return manifest

def write_object(obj, output_file_path, overwrite=False):
    setup_output_file_path(output_file_path)
    if os.path.exists(output_file_path):
        if os.path.isfile(output_file_path):
            if overwrite:
                os.remove(output_file_path)

    with open(output_file_path, 'w') as fh:
        fh.write(str(obj))

def main():
    parser = argparse.ArgumentParser(description='Generate a song payload using minimal arguments')
    parser.add_argument('-s', '--study-id', dest="study_id", help="Study ID", required=True)
    parser.add_argument('-u', '--server-url', dest="server_url", help="Server URL", required=True)
    parser.add_argument('-p', '--payload', dest="payload", help="JSON Payload", required=True)
    parser.add_argument('-o', '--output', dest="output", help="Output manifest file", required=True)
    parser.add_argument('-t', '--access-token', dest="access_token", default=os.environ.get('ACCESSTOKEN',None),help="Server URL")
    parser.add_argument('-j','--json',dest="json_output")
    results = parser.parse_args()

    study_id = results.study_id
    server_url = results.server_url
    access_token = results.access_token
    payload = results.payload

    config = ApiConfig(server_url,study_id,access_token, debug=True)
    api = Api(config)

    study_client = StudyClient(api)

    client = FileUploadClient(api, payload, is_async_validation=True,ignore_analysis_id_collisions=True)

    client.upload()
    client.update_status()
    api.save(client.upload_id, ignore_analysis_id_collisions=True)
    client.save()

    manifest_filename = results.output
    manifest_client = ManifestClient(api)
    manifest = create_manifest(api,client.analysis_id,os.path.dirname(os.path.abspath(manifest_filename)))

    with open(manifest_filename, 'w') as fh:
        fh.write(str(manifest))

    subprocess.check_output(['icgc-storage-client','upload','--manifest',manifest_filename, '--force'])

    if results.json_output:
        with open(manifest_filename,'r') as f:
            manifest_json = {}
            manifest_json['analysis_id'] = f.readline().split('\t')[0]
            manifest_json['files'] = []
            for line in f.readlines():
                _file = {}
                _file['object_id'] = line.split('\t')[0]
                _file['file_name'] = line.split('\t')[1]
                _file['md5'] = line.split('\t')[2]
                manifest_json['files'].append(_file)
            with open(results.json_output,'w') as outfile:
                json.dump(manifest_json, outfile)

    #requests.put(results.server_url+'/studies/'+results.study_id+'/analysis/publish/'+client.analysis_id,
    #             headers={"Accept": "application/json", "Content-Type": "application/json",
    #                      "Authorization": "Bearer "+results.access_token})

if __name__ == "__main__":
    main()
