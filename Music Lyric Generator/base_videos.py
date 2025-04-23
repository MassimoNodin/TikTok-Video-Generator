import os
import yt_dlp

class BaseVideoDownloader:
    def download_video(self, video_url, output_path):
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        expected_output_file = output_path + ".mp4"

        if os.path.isfile(expected_output_file):
            print(f"Video file '{expected_output_file}' already exists. Skipping download.")
            return True

        print(f"Video not found locally. Starting download for: {video_url}")
        print(f"Saving base to: {output_path}")

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_path + '.%(ext)s', # Let yt-dlp handle extension initially
            'merge_output_format': 'mp4',
            'quiet': False,
            'noplaylist': True,
            # 'verbose': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            # Check if the final MP4 file exists (after potential merge)
            if os.path.isfile(expected_output_file):
                print(f"Download successful: {expected_output_file}")
                # Clean up if yt-dlp created a file without merging (less likely with merge_output_format)
                base_name_no_ext = output_path
                if expected_output_file != base_name_no_ext + ".mp4": # Check if filename differs only by ext
                    if os.path.exists(base_name_no_ext + ".mp4") and expected_output_file != base_name_no_ext + ".mp4":
                        # This case is less likely with current opts but handles potential edge cases
                        pass # Already have the target file
                return True
            else:
                # Check if a file with the base name but different extension exists
                found_other_ext = False
                for entry in os.listdir(output_dir):
                    entry_path = os.path.join(output_dir, entry)
                    if os.path.isfile(entry_path) and os.path.splitext(entry_path)[0] == output_path:
                        print(f"Download possibly successful, but file found with different extension: {entry_path}")
                        # Attempt to rename if it's not the target mp4
                        if entry_path != expected_output_file:
                            try:
                                os.rename(entry_path, expected_output_file)
                                print(f"Renamed '{entry_path}' to '{expected_output_file}'")
                                return True
                            except OSError as rename_err:
                                print(f"Warning: Could not rename '{entry_path}' to '{expected_output_file}': {rename_err}")
                                print(f"Assuming success based on file presence, but manual check might be needed.")
                                return True # Still count as success if file exists
                        else:
                            # It was already the expected file, somehow missed above check
                            return True
                        found_other_ext = True
                        break # Found a related file

                if not found_other_ext:
                    print(f"Error: yt-dlp finished but expected output file '{expected_output_file}' not found.")
                    return False

        except yt_dlp.utils.DownloadError as e:
            print(f"Error during download for {video_url}. yt-dlp failed.")
            print(f"Error details: {e}")
            part_file = output_path + ".part"
            # Check for the expected final file first
            if os.path.exists(expected_output_file):
                try:
                    os.remove(expected_output_file)
                    print(f"Removed potentially incomplete file: {expected_output_file}")
                except OSError as rm_err:
                    print(f"Error removing incomplete file '{expected_output_file}': {rm_err}")
            elif os.path.exists(part_file):
                try:
                    os.remove(part_file)
                    print(f"Removed potentially incomplete part file: {part_file}")
                except OSError as rm_err:
                    print(f"Error removing part file '{part_file}': {rm_err}")
            # Also check for files matching the base name without specific extension
            try:
                for entry in os.listdir(output_dir):
                    entry_path = os.path.join(output_dir, entry)
                    if os.path.isfile(entry_path) and os.path.splitext(entry_path)[0] == output_path:
                        if entry_path != expected_output_file and entry_path != part_file: # Avoid double attempts
                            os.remove(entry_path)
                            print(f"Removed potentially related incomplete file: {entry_path}")
            except Exception as list_err:
                print(f"Error during cleanup check in '{output_dir}': {list_err}")

            return False
        except Exception as e:
            print(f"An unexpected error occurred during download for {video_url}: {e}")
            part_file = output_path + ".part"
            if os.path.exists(expected_output_file):
                try:
                    os.remove(expected_output_file)
                    print(f"Removed potentially incomplete file: {expected_output_file}")
                except OSError as rm_err:
                    print(f"Error removing incomplete file '{expected_output_file}': {rm_err}")
            elif os.path.exists(part_file):
                try:
                    os.remove(part_file)
                    print(f"Removed potentially incomplete part file: {part_file}")
                except OSError as rm_err:
                    print(f"Error removing part file '{part_file}': {rm_err}")
            # Also check for files matching the base name without specific extension
            try:
                for entry in os.listdir(output_dir):
                    entry_path = os.path.join(output_dir, entry)
                    if os.path.isfile(entry_path) and os.path.splitext(entry_path)[0] == output_path:
                        if entry_path != expected_output_file and entry_path != part_file:
                            os.remove(entry_path)
                            print(f"Removed potentially related incomplete file: {entry_path}")
            except Exception as list_err:
                print(f"Error during cleanup check in '{output_dir}': {list_err}")
            return False


    def sanitize_filename(self, name):
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        return safe_name if safe_name else None

    def process_video_list(self, input_file, output_dir):
        os.makedirs(output_dir, exist_ok=True)

        if not os.path.isfile(input_file):
            print(f"Error: Input file '{input_file}' not found.")
            print("Please create it with lines in the format 'name | url'.")
            return

        print(f"Reading video list from '{input_file}'...")
        download_count = 0
        skipped_count = 0
        error_count = 0
        format_error_count = 0
        total_lines = 0

        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                total_lines = len(lines)
                print(f"Found {total_lines} lines in the file.")

                for i, line in enumerate(lines):
                    line_num = i + 1
                    line = line.strip()
                    print(f"\n[{line_num}/{total_lines}] Processing line: '{line}'")

                    if not line or line.startswith('#'):
                        print("Skipping empty line or comment.")
                        continue

                    parts = line.split('|', 1)
                    if len(parts) != 2:
                        print(f"Warning: Skipping malformed line {line_num}. Expected format: 'name | url'")
                        format_error_count += 1
                        continue

                    name = parts[0].strip()
                    url = parts[1].strip()

                    if not name or not url:
                        print(f"Warning: Skipping line {line_num} with empty name or URL.")
                        format_error_count += 1
                        continue

                    safe_name = self.sanitize_filename(name)
                    if not safe_name:
                        safe_name = f"video_{line_num}"
                        print(f"Warning: Could not create a safe filename from '{name}', using '{safe_name}' instead.")

                    output_base_path = os.path.join(output_dir, safe_name)
                    output_base_path = os.path.abspath(output_base_path)
                    expected_output_path = output_base_path + ".mp4"

                    print(f"Processing '{name}' ({url})...")

                    was_present_before = os.path.isfile(expected_output_path)

                    # Pass the base path (without extension)
                    success = self.download_video(url, output_base_path)

                    if success:
                        if was_present_before:
                            skipped_count += 1
                        else:
                            if os.path.isfile(expected_output_path):
                                download_count += 1
                            else:
                                # This case is handled more robustly within download_video now
                                # but we keep a check here for sanity.
                                print(f"Warning: Download reported success for '{name}', but expected file '{expected_output_path}' not found post-call. Check logs.")
                                error_count += 1 # Count as error if final expected file isn't there
                    else:
                        error_count += 1

        except FileNotFoundError:
            print(f"Error: Input file '{input_file}' not found during processing.")
            return
        except Exception as e:
            print(f"An unexpected error occurred while processing the list: {e}")
            error_count += (total_lines - (download_count + skipped_count + format_error_count + error_count)) # Estimate remaining as errors

        print(f"\n--- Download Summary ---")
        print(f"Processed {total_lines} lines from '{input_file}'.")
        print(f"Successfully downloaded: {download_count}")
        print(f"Skipped (already existed): {skipped_count}")
        print(f"Errors during download: {error_count}")
        print(f"Skipped lines due to format issues: {format_error_count}")
        print(f"Videos stored in: {os.path.abspath(output_dir)}")