#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
from overture_song.model import ApiConfig, Manifest, ManifestEntry
from overture_song.client import Api, ManifestClient, StudyClient
from overture_song.tools import FileUploadClient
from overture_song.utils import setup_output_file_path
import subprocess
import requests


def create_manifest(api,analysis_id, manifest_file,files_dir):
    manifest = Manifest(analysis_id)
    with open(os.path.join(files_dir,manifest_file), 'w') as outfile:
        outfile.write(analysis_id+'\t\t\n')
        for i in range(0,len(api.get_analysis_files(analysis_id))):
            file_object = api.get_analysis_files(analysis_id)[i]
            outfile.write(file_object.objectId+'\t'+os.path.join(files_dir,file_object.fileName)+'\t'+file_object.fileMd5sum+'\n')

def exists_in_file_array(file_name, file_md5, file_size, file_type, file_access, files_array):
    for i in range(0, len(files_array)):
        if file_name == files_array[i].get('fileName') and \
            file_md5 == files_array[i].get('fileMd5sum') and\
            file_size == files_array[i].get('fileSize') and \
            file_type == files_array[i].get('fileType') and \
            file_access == files_array[i].get('fileAccess'):
            return True
    return False



def main():
    parser = argparse.ArgumentParser(description='Generate a song payload using minimal arguments')
    parser.add_argument('-s', '--study-id', dest="study_id", help="Study ID", required=True)
    parser.add_argument('-u', '--server-url', dest="server_url", help="Server URL", required=True)
    parser.add_argument('-p', '--payload', dest="payload", help="JSON Payload", required=True)
    parser.add_argument('-o', '--output', dest="output", help="Output manifest file", required=True)
    parser.add_argument('-d', '--input-dir', dest="input_dir", help="Payload files directory", required=True)
    parser.add_argument('-t', '--access-token', dest="access_token", default=os.environ.get('ACCESSTOKEN',None),help="Server URL")
    parser.add_argument('-j','--json',dest="json_output")
    results = parser.parse_args()

    study_id = results.study_id
    server_url = results.server_url
    access_token = results.access_token
    payload = results.payload
    analysis_id = json.load(open(payload)).get('analysisId')

    config = ApiConfig(server_url,study_id,access_token, debug=True)
    api = Api(config)

    client = FileUploadClient(api, payload, is_async_validation=True, ignore_analysis_id_collisions=True)

    analysis = None
    try:
        analysis = api.get_analysis(analysis_id)

        if analysis is '':
            raise Exception('Analysis id ' + analysis_id + ' not found')

        payload_files = json.load(open(payload)).get('file')
        api_files = api.get_analysis_files(analysis_id)

        for i in range(0,len(api_files)):
            if not exists_in_file_array(
                file_name = api_files[i].fileName,
                file_md5 = api_files[i].fileMd5sum,
                file_type = api_files[i].fileType,
                file_size = api_files[i].fileSize,
                file_access = api_files[i].fileAccess,
                files_array = payload_files):
                print("Files in  payload do not match the files on song server.")
                exit(1)
    except Exception:
        if analysis is None or analysis is '':
            client.upload()
            client.update_status()
            client.save()

    manifest_filename = results.output
    create_manifest(api,analysis_id,manifest_filename,results.input_dir)


    subprocess.check_output(['icgc-storage-client','upload','--manifest',os.path.join(results.input_dir,manifest_filename), '--force'])

    api.publish(analysis_id)
    #client.publish()

    if results.json_output:
        with open(os.path.join(results.input_dir,manifest_filename),'r') as f:
            manifest_json = {}
            manifest_json['analysis_id'] = f.readline().split('\t')[0]
            manifest_json['files'] = []
            for line in f.readlines():
                _file = {}
                _file['object_id'] = line.split('\t')[0]
                _file['file_name'] = line.split('\t')[1]
                _file['md5'] = line.split('\t')[2]
                manifest_json['files'].append(_file)
            with open(os.path.join(results.input_dir,results.json_output),'w') as outfile:
                json.dump(manifest_json, outfile)

    #requests.put(results.server_url+'/studies/'+results.study_id+'/analysis/publish/'+client.analysis_id,
    #             headers={"Accept": "application/json", "Content-Type": "application/json",
    #                      "Authorization": "Bearer "+results.access_token})

if __name__ == "__main__":
    main()
