import speech_recognition as sr
from tqdm import tqdm
import glob
import os
from os import path
import subprocess


with open("api-key.json") as f:
    GOOGLE_CLOUD_SPEECH_CREDENTIALS = f.read()


class Paths:
    incoming = "incoming/"
    working = "working/"
    parts = "parts/"


class WorkItem:
    pickup_filepath = ""
    mp3_filename = None
    workpath = None
    workpath_parts = None
    wav_filepath = None
    transcript_filepath = None

    def __init__(self, pickup_filepath):
        self.pickup_filepath = pickup_filepath
        self.mp3_filename = os.path.basename(self.pickup_filepath)
        self.workpath = os.path.join(Paths.working, self.mp3_filename)
        self.workpath_parts = os.path.join(self.workpath, Paths.parts)
        # wav file name and path
        name = os.path.basename(self.pickup_filepath)
        wav_fname = filename_replace_ext(name, "wav")
        self.wav_filepath = os.path.join(self.workpath, wav_fname)
        self.transcript_filepath = os.path.join(self.workpath, "transcript.txt")
    def workpath_exists(self) -> bool:
        return not self.workpath is None and os.path.exists(self.workpath)
    def init_work_paths(self):
        # make work path matching mp3 name
        if not os.path.exists(self.workpath_parts):
            os.makedirs(self.workpath_parts)
    def __str__(self):
        return f"<Item: {self.pickup_filepath} in {self.workpath} >"


def init_paths(paths = [Paths.incoming, Paths.working]):
    """ make paths; defaults to all defined in class """
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)


def reset_for_new_run(self):
    """ perform clean up """
    # shutil.rmtree(Paths.parts)
    # self.make_paths(Paths.parts)
    pass


def files_list(path, ext='mp3'):
    """ grab list of mp3 files in path, or other if you override 'ext' """
    path = os.path.join(path, f"*.{ext}")
    # print(f"Find files in {path}")
    files = sorted([f for f in glob.glob(path)])
    # print(files)
    # now have list of files
    #['incoming/1.mp3', 'incoming/2.mp3']
    return files


def filename_replace_ext(filename, replace_ext):
    name, ext = filename.split('.')
    return f"{name}.{replace_ext}"


def transcode_mp3_to_wav(mp3_in, wav_out):
    """ transcode mp3 to wav """
    print(f"\t> Processing in:{mp3_in} out:{wav_out}")
    subprocess.run(["ffmpeg", "-i", mp3_in, wav_out], capture_output=True)


def make_wav_parts(wi: WorkItem):
    print(f"\t> Making parts from wav...")
    # ffmpeg -i source/$1 -f segment -segment_time 59 -c copy parts/out%09d.wav
    cmd = ["ffmpeg", "-i", wi.wav_filepath, "-f", "segment", "-segment_time", "59", "-c", "copy", f"{wi.workpath_parts}/out%09d.wav"]
    # print(cmd)
    subprocess.run(cmd, capture_output=True)

# process all parts/*.wav files
# clear parts/* after done
def process_parts_wav(wi: WorkItem):
    r = sr.Recognizer()
    files = sorted([f for f in glob.glob(f"{wi.workpath_parts}/*.wav")])
    all_text = []
    for name in tqdm(files):
        # Load audio file
        with sr.AudioFile(name) as source:
            audio = r.record(source)
        # Transcribe audio file
        text = r.recognize_google_cloud(audio, credentials_json=GOOGLE_CLOUD_SPEECH_CREDENTIALS)
        # text = r.recognize_google_cloud(audio)
        all_text.append(text)

    transcript = ""
    for i, t in enumerate(all_text):
        total_seconds = i * 30
        # Cool shortcut from:
        # https://stackoverflow.com/questions/775049/python-time-seconds-to-hms
        # to get hours, minutes and seconds
        m, s = divmod(total_seconds, 60)
        h, m = divmod(m, 60)

        # Format time as h:m:s - 30 seconds of text
        transcript = transcript + "{:0>2d}:{:0>2d}:{:0>2d} {}\n".format(h, m, s, t)
    
    # print(transcript)
    with open(wi.transcript_filepath, "w") as f:
        f.write(transcript)


if __name__ == "__main__":
    # init paths
    init_paths()
    # get mp3 files in 'incoming'
    mp3_files = files_list(Paths.incoming)
    for mp3_f_item in mp3_files:
        # f_item_base = os.path.basename(mp3_f_item)
        work_item = WorkItem(mp3_f_item)
        print(f"Process item: {work_item}")
        # for mp3 filename from list
        # check if mp3 filename has working/processed dir in 'working'; ignore if exists; log and pick next item
        if work_item.workpath_exists():
            # already exists, ignore and pick next file
            # TODO log
            print(f"\t > Exists, ignoring... {work_item.workpath}/")
            continue
        # if not exist...
        # create folder same name as wav file in 'working' == item_working_path
        work_item.init_work_paths()
        # transcode mp3 to wav and place in this working path
        transcode_mp3_to_wav(work_item.pickup_filepath, work_item.wav_filepath)
        # run parts to output
        make_wav_parts(work_item)

        # run to process item_working_path/'parts'
        # when done make a .done file
        # create transcode file in work path
        process_parts_wav(work_item)
    
    print("----\nDone")
