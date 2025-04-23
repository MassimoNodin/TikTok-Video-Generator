from base_videos import BaseVideoDownloader

if __name__ == "__main__":
    base_videos_file = "base_videos.txt"
    output_directory = "base_videos"
    BaseVideoDownloader.process_video_list(base_videos_file, output_directory)