import os
from flask import Flask, request, jsonify
import paramiko

app = Flask(__name__)

# Ambil data sensitif dari Environment Variables Render
SFTP_HOST = os.environ.get("SFTP_HOST", "149.129.254.152")
SFTP_PORT = int(os.environ.get("SFTP_PORT", 22))
SFTP_USER = os.environ.get("SFTP_USER", "")
SFTP_PASS = os.environ.get("SFTP_PASS", "")

@app.route('/upload', methods=['POST'])
def upload_sftp():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Payload JSON tidak ditemukan"}), 400

    folder_id = data.get("folder_id") # Contoh: NC4766
    files = data.get("files", [])     # List file: [{filename: "...", content: "..."}, ...]

    if not folder_id or not files:
        return jsonify({"status": "error", "message": "folder_id atau files tidak boleh kosong"}), 400

    try:
        # Transpor SSH & SFTP Connection
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASS)
        sftp = paramiko.SFTPClient.from_transport(transport)

        # Path tujuan utama di server SFTP
        base_path = "/home/Live/in/DataToScyllaPro"
        target_dir = f"{base_path}/{folder_id}"

        # Buat folder jika belum ada
        try:
            sftp.stat(target_dir)
        except FileNotFoundError:
            sftp.mkdir(target_dir)

        # Upload setiap file
        for f in files:
            remote_file_path = f"{target_dir}/{f['filename']}"
            with sftp.open(remote_file_path, 'w') as remote_file:
                remote_file.write(f['content'])

        sftp.close()
        transport.close()

        return jsonify({
            "status": "success",
            "message": f"Berhasil membuat/mengupdate folder {folder_id} dan mengunggah {len(files)} file."
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
