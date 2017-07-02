from PySide2 import QtCore

from AWS_Vault_core.awsv_io import *

""" 
    All threads ( Runnable objects ) used in the interface for cloud <=> ui interaction
    These threads will be launched using a QThreadPool global instance.
"""

# Thread used to fetch cloud and local files from a fiven folder
class ElementFetcherSignals(QtCore.QObject):

    start_sgn = QtCore.Signal()
    end = QtCore.Signal()
    add_element = QtCore.Signal(str)  # file key
    add_folder = QtCore.Signal(str)  # folder name

class ElementFetcherThread(QtCore.QRunnable):

    def __init__(self):
        super(ElementFetcherThread, self).__init__()

        self.setAutoDelete(True)
        
        self.data = None
        self.bucket = None
        self.folder_name = ""
        self.cancel = False

        # get list of skipped folders from config.ini
        self.skipped_folders = Config.get("Folders",
                                          "LocalSkippedFolders",
                                          str).split(',')
        self.skipped_folders_CS = Config.get("Folders",
                                             "SkippedFoldersCaseSensitive",
                                             bool)
        if not self.skipped_folders_CS:
            self.skipped_folders = [n.lower() for n in self.skipped_folders]

        self.signals = ElementFetcherSignals()

    def run(self):

        local_root = ConnectionInfos.get("local_root")
        Bucket = ConnectionInfos.get("bucket")

        folders_sent = []
        elements_sent = []

        # Get cloud folders
        if Bucket:
            if self.folder_name != "":
                if not self.folder_name.endswith('/'): self.folder_name += '/'
            s3_client = ConnectionInfos.get("s3_client")

            Logger.Log.debug("Get cloud folder elements " + self.folder_name)

            if self.cancel: return

            raw = s3_client.list_objects_v2(Bucket=Bucket.name, Prefix=self.folder_name, Delimiter='/')

            prefixes = raw.get("CommonPrefixes")
            if prefixes:
                for f in [f["Prefix"][0:-1] for f in prefixes]:
                    if self.cancel: return
                    if f in folders_sent: continue
                    self.signals.add_folder.emit(f)
                    folders_sent.append(f)

            raw_contents = raw.get("Contents")
            if raw_contents:
                for f in [c["Key"] for c in raw_contents]:
                    if self.cancel: return
                    if f.endswith('/'):
                        continue
                    if f.endswith(awsv_objects.METADATA_IDENTIFIER):
                        continue
                    if f in elements_sent:
                        continue
                    self.signals.add_element.emit(f)
                    elements_sent.append(f)
        else:
            Logger.Log.warning("Bucket is None, can't get cloud elements")

        # Get local folders and elements
        folder = local_root + self.folder_name

        Logger.Log.debug("Get local folder elements " + folder)

        elements = os.listdir(folder)
        local_root = ConnectionInfos.get("local_root")
        clean_root = folder.replace('\\', '/').replace(local_root, '')
        if clean_root == '/': clean_root = ''
        if clean_root.startswith('/'): clean_root = clean_root[1:]

        for element in elements:
            
            if self.cancel: return

            el = folder + element
            if not os.path.exists(el):
                continue

            if os.path.isdir(el):
                
                check_el = element
                if not self.skipped_folders_CS:
                    check_el = element.lower()

                if check_el in self.skipped_folders:
                    Logger.Log.debug("Folder {} found in LocalSkippedFolders: skipped.".format(element))
                    continue

                if clean_root != "":
                    f = clean_root + element
                else:
                    f = element

                if f in folders_sent: continue
                self.signals.add_folder.emit(f)
                folders_sent.append(f)

            else:
                if element.endswith(awsv_objects.METADATA_IDENTIFIER):
                    remove_unused_metadata(el)
                    continue
                else:
                    f = clean_root + element
                    if f in elements_sent: continue
                    self.signals.add_element.emit(f)
                    elements_sent.append(f)

        self.signals.end.emit()

# Thread used when a state of a file is fetched from the cloud
class FetchStateSignals(QtCore.QObject):

    start_sgn = QtCore.Signal()
    end_sgn = QtCore.Signal(str, dict)

class FetchStateThread(QtCore.QRunnable):

    def __init__(self, local_file_path):
        super(FetchStateThread, self).__init__()

        self.setAutoDelete(True)

        self.local_file_path = local_file_path
        self.signals = FetchStateSignals()

    def run(self):

        self.signals.start_sgn.emit()
        file_state, metadata = refresh_state(self.local_file_path)
        self.signals.end_sgn.emit(file_state, metadata)

# Files IO thread used when a file is being sent to the cloud
# or downloaded from the cloud.
class FileIOSignals(QtCore.QObject):

    start_sgn = QtCore.Signal(int)
    update_progress_sgn = QtCore.Signal(int)
    end_sgn = QtCore.Signal(int)

class FileIOThread(QtCore.QRunnable):

    
    def __init__(self, local_file_path, mode=0, message="",
                 keep_locked=False, version_id=None):
        """ mode: 0 => upload, 1 => download
        """
        super(FileIOThread, self).__init__()

        self.setAutoDelete(True)
        self.signals = FileIOSignals()

        self.local_file_path = local_file_path
        self.keep_locked = keep_locked
        self.mode = mode
        self.message = message
        self.version_id = version_id

    def update_progress(self, progress):
        
        self.signals.update_progress_sgn.emit(progress)
    
    def run(self):
        
        self.signals.start_sgn.emit(self.mode)
        if self.mode == 0:
            send_object(self.local_file_path, message=self.message,
                        callback=self.update_progress, keep_locked=self.keep_locked)
        else:
            get_object(self.local_file_path, callback=self.update_progress,
                       version_id=self.version_id)
        self.signals.end_sgn.emit(self.mode)
    
# Unique thread object to download an entire project
class DownloadProjectThread(QtCore.QThread):

    start_sgn = QtCore.Signal()
    start_element_download_sgn = QtCore.Signal(str, int)  # element name, element size ( bytes )
    update_download_progress_sgn = QtCore.Signal(int)  # bytes downloaded
    end_sgn = QtCore.Signal(int, int, str, int)  # statue, number of item downloaded, time spent, total size

    def __init__(self, bucket, local_path):
        super(DownloadProjectThread, self).__init__()

        self.bucket = bucket
        self.local_path = local_path + '/'
        self.cancel = False

    def update_progress(self, b):

        self.update_download_progress_sgn.emit(b)

    def run(self):

        start_time = datetime.datetime.now()

        self.start_sgn.emit()
        try:
            Logger.Log.info("Fetching all bucket's objects")
            all_objects = self.bucket.objects.all()
        except Exception as e:
            Logger.Log.error(str(e))
            self.end_sgn.emit(-1, 0, str(e))
            return

        n_elements = 0
        global_size = 0

        for obj in all_objects:
            
            if self.cancel:
                Logger.Log.info("Cancelling project download ...")
                self.end_sgn.emit(0, n_elements, "", global_size)
                return

            key = obj.key

            # create folder
            if key.endswith('/'):
                key = key[0:-1]
                os.makedirs(self.local_path + key)
                continue
            
            # download object
            path = self.local_path + key
            _object = obj.Object()
            
            self.start_element_download_sgn.emit(key, obj.size)

            try:
                Logger.Log.debug("Downloading file: " + path)
                _object.download_file(path, Callback=self.update_progress)
            except Exception as e:
                Logger.Log.error(str(e))
                self.end_sgn.emit(-1, 0, str(e), 0)
                return

            n_elements += 1
            global_size += obj.size

        end_time = datetime.datetime.now()

        time_elapsed = str(end_time - start_time)

        self.end_sgn.emit(1, n_elements, time_elapsed, global_size)
        Logger.Log.info("Project files downloaded !")