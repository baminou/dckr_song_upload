#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
from overture_song.model import ApiConfig, Manifest, ManifestEntry, SongError
from overture_song.client import Api, ManifestClient, StudyClient
from overture_song.tools import FileUploadClient
from overture_song.utils import setup_output_file_path
import subprocess
import requests


def create_manifest(song_server, study_id, payload_json, manifest_file,files_dir):

    with open(os.path.join(files_dir,manifest_file), 'w') as outfile:
        outfile.write(payload_json.get('analysisId')+'\t\t\n')
        for i in range(0,len(payload_json.get('file'))):
            file_object = payload_json.get('file')[i]
            outfile.write(retrieve_object_id(song_server,study_id, payload_json.get('analysisId'),
                                             file_object.get('fileName'),
                                             file_object.get('fileMd5sum'))+'\t'+os.path.join(files_dir,file_object.get('fileName'))+'\t'+file_object.get('fileMd5sum')+'\n')
    return

def retrieve_object_id(song_server, study_id, analysis_id, file_name, file_md5sum):
    analysis = get_analysis(song_server, study_id, analysis_id)
    for file in analysis.get('file'):
        if file.get('fileName') == file_name and file.get('fileMd5sum') == file_md5sum:
            return file.get('objectId')
    raise Exception('The object id could not be found for '+file_name)

def get_analysis(song_server, study_id, analysis_id):
    response = requests.get(song_server+'/studies/'+study_id+'/analysis/'+analysis_id)
    if response.status_code >=400:
        raise Exception("The analysis %s does not exist." % analysis_id)
    return response.json()

def validate_payload_against_analysis(api,analysis_id, payload_file):
    json_data = json.load(open(payload_file))
    payload_files = []
    for file in json_data.get('file'):
        payload_files.append(file)

    for file in api.get_analysis_files(analysis_id):
        tmp_file = {'fileName':file.fileName,'fileSize':file.fileSize,'fileType':file.fileType,'fileMd5sum':file.fileMd5sum,'fileAccess':file.fileAccess}
        if not tmp_file in payload_files:
            raise Exception("The payload to be uploaded and the analysis on SONG do not match.")
    return True

def main():
    parser = argparse.ArgumentParser(description='Upload a payload using SONG')
    parser.add_argument('-s', '--study-id', dest="study_id", help="Study ID", required=True)
    parser.add_argument('-u', '--server-url', dest="server_url", help="Server URL", required=True)
    parser.add_argument('-p', '--payload', dest="payload", help="JSON Payload", required=True, type=argparse.FileType('r'))
    parser.add_argument('-t', '--access-token', dest="access_token", default=os.environ.get('ACCESSTOKEN',None),help="Server URL")
    parser.add_argument('-d', '--input-dir', dest="input_dir", help="Payload files directory", required=True)
    parser.add_argument('-o', '--output', dest="output", help="Output manifest file", required=True)

    results = parser.parse_args()

    payload = json.load(results.payload)

    #validate_payload(results.server_url, results.study_id, payload)
    upload_id = upload_payload(results.server_url, results.study_id, payload, results.access_token)
    validate_upload(results.server_url,results.study_id, upload_id)
    save_upload(results.server_url,results.study_id, upload_id, results.access_token, True)

    if not analysis_state(results.server_url,results.study_id, payload.get('analysisId')) == 'UNPUBLISHED':
        raise Exception("The payload hasn't been correctly uploaded and should be in UNPUBLISHED state: %s")

    manifest_filename = results.output
    create_manifest(results.server_url, results.study_id, payload, manifest_filename,results.input_dir)
    subprocess.check_output(['/Users/baminou/Downloads/icgc-storage-client/bin/icgc-storage-client', 'upload', '--manifest', os.path.join(results.input_dir, manifest_filename), '--force'])

    if not analysis_state(results.server_url, results.study_id, payload.get('analysisId')) == 'PUBLISHED':
        raise Exception("The analysis %s should be in a PUBLISHED state." % payload.get('analysisId'))

    return

def upload_payload(song_server, study_id, payload_json, access_token):
    response = requests.post(song_server+'/upload/'+study_id,json=payload_json,headers={'Authorization': 'Bearer '+access_token,'Content-Type': 'application/json'})
    if response.status_code >= 400:
        raise Exception(response.text)
    return response.json().get('uploadId')

def validate_upload(song_server, study_id, upload_id):
    upload = get_upload(song_server, study_id, upload_id)
    if upload.get('state') == "VALIDATION_ERROR":
        raise Exception(upload.get('errors')[0])
    elif upload.get('state') == "VALIDATED":
        return True
    else:
        raise Exception("The upload %s is in an unknown state." % upload_id)

def get_upload(song_server, study_id, upload_id):
    response = requests.get(song_server+'/upload/'+study_id+'/status/'+upload_id)
    if response.status_code >= 400:
        raise Exception("The upload %s does not exist." % upload_id)
    return response.json()

def save_upload(song_server, study_id, upload_id, access_token, ignoreAnalysisIdCollisions=False):
    response = requests.post(song_server+'/upload/'+study_id+'/save/'+upload_id+'?ignoreAnalysisIdCollisions='+str(ignoreAnalysisIdCollisions).lower()
                             ,headers={'Authorization': 'Bearer '+access_token,'Content-Type': 'application/json'})
    if response.status_code >= 400:
        raise Exception(response.json().get('message'))

def validate_payload(song_server, study_id, payload_json):
    if not song_is_alive(song_server=song_server):
        raise Exception("The SONG server you are trying to reach is not available: %s" % song_server)

    if not study_exists(song_server=song_server, study_id=study_id):
        raise Exception("Study %s does not exist on the SONG server %s" % (study_id, song_server))

    if not study_is_allowed(song_server=song_server, study_id=study_id):
        raise Exception("The study %s is not allowed on the server %s" % (study_id, song_server))

    if not payload_matching_study(study_id=study_id, payload_json=payload_json):
        raise Exception("The study in the payload %s does not match the study you are trying to upload to %s" % (payload_json.get('study'),study_id))

    if analysis_id_exists(song_server=song_server, study_id=study_id, analysis_id=payload_json.get('analysisId')):
        state = analysis_state(song_server=song_server, study_id=study_id,analysis_id=payload_json.get('analysisId'))
        if state == 'PUBLISHED':
            raise Exception("The analysisId %s you try to upload already exists on %s." % (payload_json.get('analysisId'), song_server))

    return

def study_exists(song_server, study_id):
    response = requests.get(song_server+'/studies/'+study_id)
    return response.status_code==200

def song_is_alive(song_server):
    try:
        response = requests.get(song_server+'/isAlive')
        return response.text == 'true'
    except requests.exceptions.ConnectionError as err:
        return False

def study_is_allowed(song_server, study_id):
    allowed_codes = {'LIRI-JP', 'PACA-CA', 'PRAD-CA', 'RECA-EU', 'PAEN-AU', 'PACA-AU',
                     'BOCA-UK', 'OV-AU', 'MELA-AU', 'BRCA-UK', 'PRAD-UK', 'CMDI-UK', 'LINC-JP',
                     'ORCA-IN', 'BTCA-SG', 'LAML-KR', 'LICA-FR', 'CLLE-ES', 'ESAD-UK', 'PAEN-IT'}
    if "virginia" in str(song_server).lower() and study_id not in allowed_codes:
        return False
    return True

def payload_matching_study(study_id, payload_json):
    if not 'study' in payload_json:
        raise Exception("The study field is missing in the payload.")
    return str(study_id) == str(payload_json.get('study'))

def analysis_id_exists(song_server, study_id, analysis_id):
    response = requests.get(song_server+'/studies/'+study_id+'/analysis/'+analysis_id)
    return response.status_code < 300

def analysis_state(song_server, study_id, analysis_id):
    if not analysis_id_exists(song_server, study_id, analysis_id):
        raise Exception("The analysis id %s does not exist on the server %s." % (analysis_id, song_server))
    response = requests.get(song_server+'/studies/'+study_id+'/analysis/'+analysis_id)
    return response.json().get('analysisState')





if __name__ == "__main__":
    main()
