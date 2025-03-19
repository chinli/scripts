#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import configparser
import hashlib
import imaplib
import email
import os
from email.header import decode_header
from datetime import datetime
import subprocess
from gerrit import Gerrit
import re

VERSION = "2025.3"
CONFIG_FILE = 'conf.ini'

def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return {
        'imap_server': config['EMAIL']['IMAP_SERVER'],
        'imap_port': int(config['EMAIL']['IMAP_PORT']),
        'email': config['EMAIL']['EMAIL'],
        'password': config['EMAIL']['PASSWORD'],
        'gerrit_url': config['GERRIT']['URL'],
        'gerrit_http_url': config['GERRIT']['HTTP_URL'],
        'gerrit_prj': config['GERRIT']['PROJECT'],
        'gerrit_branch': config['GERRIT']['BRANCH'],
        'gerrit_username': config['GERRIT']['USERNAME'],
        'gerrit_password': config['GERRIT']['PASSWORD'],
        'output_dir': config.get('DEFAULT', 'OUTPUT_DIR', fallback='patches'),
        'code_base_dir': config['DEFAULT']['CODE_BASE_DIR']
    }

def connect_mail_server(config):
    try:
        mail = imaplib.IMAP4_SSL(config['imap_server'], config['imap_port'])
        mail.login(config['email'], config['password'])
        return mail
    except imaplib.IMAP4.error as e:
        print(f"详细错误信息: {str(e)}")
        raise

def process_emails(mail, output_dir):
    mail.select('INBOX')
    files = []

    status, messages = mail.search(None, '(UNSEEN SUBJECT "PATCH")')

    for num in messages[0].split():
        try:
            typ, msg_data = mail.fetch(num, '(RFC822)')
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = decode_subject(msg['Subject'])

            patch_content = extract_patch_content(msg)
            patch_content = patch_content.replace('\r\n', '\n')
            if patch_content:
                filename = generate_filename(subject, output_dir)

                with open(filename, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(patch_content)
                print(f"save patch: {filename}")

                files.append(filename)

            #    mail.store(num, '+FLAGS', '\\Seen')
        except Exception as e:
            print(f"error: {str(e)}")
    return files

def decode_subject(encoded_subject):
    subject, encoding = decode_header(encoded_subject)[0]
    if isinstance(subject, bytes):
        return subject.decode(encoding or 'utf-8')
    return subject

def extract_patch_content(msg):
    # check attachment
    for part in msg.walk():
        content_disposition = str(part.get("Content-Disposition"))
        if "attachment" in content_disposition:
            filename = part.get_filename()
            if filename and filename.endswith('.patch'):
                return part.get_payload(decode=True).decode('utf-8')

    # check body
    for part in msg.walk():
        if part.get_content_type() == 'text/plain':
            body = part.get_payload(decode=True).decode('utf-8')
            if 'diff --git' in body:
                return body
    return None

def generate_filename(subject, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    safe_subject = subject.replace(':', '_').replace(' ', '_').replace('/', '_')[:50]
    return os.path.join(output_dir, f"{safe_subject}.patch")

def generate_change_id():
    # 获取提交信息
    commit_info = subprocess.check_output(['git', 'log', '-1', '--pretty=%B']).decode('utf-8')
    commit_info = commit_info.strip()

    # 获取作者信息
    author_info = subprocess.check_output(['git', 'log', '-1', '--pretty=%an <%ae>%n%ad']).decode('utf-8')
    author_info = author_info.strip()

    # 获取树对象
    tree_hash = subprocess.check_output(['git', 'log', '-1', '--pretty=%T']).decode('utf-8').strip()

    # 获取父对象
    parent_hash = subprocess.check_output(['git', 'log', '-1', '--pretty=%P']).decode('utf-8').strip()

    # 生成 Change-Id
    change_id_input = f"tree {tree_hash}\nparent {parent_hash}\nauthor {author_info}\ncommitter {author_info}\n\n{commit_info}\n"
    change_id = 'I' + hashlib.sha1(change_id_input.encode('utf-8')).hexdigest()
    print(f"Change-Id: {change_id}")
    return change_id

def apply_patch(patch_file_path, code_base_dir, branch):
    try:
        os.chdir(code_base_dir)
        subprocess.run(['git', 'checkout', branch], check=True)
        subprocess.run(['git', 'reset', '--hard', 'origin/' + branch], check=True)
        subprocess.run(['git', 'pull', 'origin', branch], check=True)
        subprocess.run(['git', 'apply', patch_file_path], check=True)
        print(f"Apply {patch_file_path} susccessfully")
    except subprocess.CalledProcessError as e:
        print(f"Apply failed: {e}")
        return False
    return True

def commit_patch(patch_file_path):
    try:
        change_id = generate_change_id()

        with open(patch_file_path, 'r', encoding='utf-8') as f:
            patch_content = f.read()

        signofby_txt = [line for line in patch_content.split('\n') if line.startswith('Signed-off-by:')]
        signofby = '\n'.join(signofby_txt)

        subprocess.run(['git', 'add', '.'], check=True)
        commit_message = f"Apply patch {os.path.basename(patch_file_path)}\n\nChange-Id: {change_id}\n{signofby}"
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        print(f"Commit {patch_file_path} susccessfully")
    except subprocess.CalledProcessError as e:
        print(f"Commit Failed: {e}")
        return False
    return True

def push_to_gerrit(gerrit_url, gerrit_branch):
    try:
        gerrit_branch = gerrit_branch.strip("'\"")
        push_target = f'HEAD:refs/for/{gerrit_branch}'
        result = subprocess.run(['git', 'push', gerrit_url, push_target], check=True, capture_output=True, text=True)
        print("Push Gerrit susccessfully ")
        #print("result info:", result)
        return result.returncode, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"Push Gerrit failed: {e}")
        return None

def set_verified_score(change_id, gerrit_url, gerrit_username, gerrit_password):
    print(f"Set verified score for {change_id}")
    gerrit = Gerrit(gerrit_url, gerrit_username, gerrit_password)
    message  = "Auto Verified by AMLRobot"
    response = gerrit.post_review_pass_message(change_id, message)
    print(response)

def extract_change_id(push_output):
    match = re.search(r'https://scgit\.amlogic\.com/(\d+)', push_output)
    if match:
        return match.group(1)
    return None

if __name__ == "__main__":
    try:
        config = load_config()
        mail = connect_mail_server(config)
        patch_list = process_emails(mail, config['output_dir'])
        mail.close()
        mail.logout()
        print(f"Patch list: {patch_list}")
        current_dir = os.path.dirname(os.path.abspath(__file__))

        #patch_list = ['patches/[PATCH_1_1]_For_test_robot_jenkins.patch']
        for patch in patch_list:
            patch_path = os.path.join(current_dir, patch)
            if apply_patch(patch_path, config['code_base_dir'], config['gerrit_branch'].strip("'\"")):
                if commit_patch(patch_path):
                    push_url = config['gerrit_url'].strip("'\"") + config['gerrit_prj'].strip("'\"")
                    retval, cl_link = push_to_gerrit(push_url, config['gerrit_branch'])
                    if retval == 0:
                        set_verified_score(extract_change_id(cl_link),
                                           config['gerrit_http_url'].strip("'\""),
                                           config['gerrit_username'].strip("'\""),
                                           config['gerrit_password'].strip("'\""))

    except Exception as e:
        print(f"Error: {str(e)}")