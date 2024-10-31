from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import concatenate_videoclips, ImageSequenceClip, VideoFileClip
import numpy as np
import re
import os

def split_sentences(text):
    sentences = re.split(r'(?<=[.!?,])\s*', text.strip())
    return [sentence.strip() for sentence in sentences if sentence]  # Filter out empty sentences

def resize_to_aspect_ratio_with_zoom(image, target_aspect_ratio, target_resolution=(1080, 1920)):
    original_width, original_height = image.size
    original_aspect_ratio = original_width / original_height

    if original_aspect_ratio < target_aspect_ratio:
        new_height = target_resolution[1]
        new_width = int(new_height * original_aspect_ratio)
    else:
        new_width = target_resolution[0]
        new_height = int(new_width / original_aspect_ratio)

    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    new_image = Image.new("RGB", target_resolution, (0, 0, 0))
    x_offset = (target_resolution[0] - new_width) // 2
    y_offset = (target_resolution[1] - new_height) // 2
    new_image.paste(resized_image, (x_offset, y_offset))

    return new_image

def stretch_vertically_to_resolution(image, target_resolution=(1080, 1920)):
    stretched_image = image.resize(target_resolution, Image.Resampling.LANCZOS)
    return stretched_image

def add_centered_text_with_outline(image, text, font_path, font_size, text_color):
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, font_size)
    max_width = int(image.size[0] * 0.85)

    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]

        if line_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    total_height = sum(
        draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines
    ) + (len(lines) - 1) * 10
    y_position = (image.size[1] - total_height) // 2

    for line in lines:
        text_bbox = draw.textbbox((0, 0), line, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        x_position = (image.size[0] - text_width) // 2

        outline_color = (255, 255, 255) if text_color == (0, 0, 0) else (0, 0, 0)
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    draw.text((x_position + dx, y_position + dy), line, font=font, fill=outline_color)

        draw.text((x_position, y_position), line, font=font, fill=text_color)
        y_position += text_bbox[3] - text_bbox[1] + 10

    return image

def create_video_from_image_with_text(image_path, output_video_path, text, font_path, font_size, text_color,
                                      total_duration, method='zoom'):
    image = Image.open(image_path).convert("RGB")
    if method == 'zoom':
        image = resize_to_aspect_ratio_with_zoom(image, 9 / 16)  # Zoom the image
    else:
        image = stretch_vertically_to_resolution(image)  # Stretch the image vertically

    sentences = split_sentences(text)
    sentence_duration = total_duration / len(sentences) if sentences else 0

    clips = []
    for sentence in sentences:
        frame_image = add_centered_text_with_outline(image.copy(), sentence, font_path, font_size, text_color)
        frame_array = np.array(frame_image)

        text_clip = ImageSequenceClip([frame_array], fps=24).set_duration(sentence_duration)
        clips.append(text_clip)

    final_clip = concatenate_videoclips(clips, method="compose")
    final_clip.write_videofile(output_video_path, codec='libx264', bitrate="5000k", fps=24)

def create_video_from_video_with_text(video_path, output_video_path, text, font_path, font_size, text_color,
                                      total_duration, method='zoom'):
    video_clip = VideoFileClip(video_path)
    trimmed_clip_duration = min(total_duration, video_clip.duration)

    sentences = split_sentences(text)
    sentence_duration = trimmed_clip_duration / len(sentences) if sentences else 0
    clips = []

    for i, sentence in enumerate(sentences):
        start_time = i * sentence_duration
        end_time = (i + 1) * sentence_duration
        sentence_clip = video_clip.subclip(start_time, end_time)

        frame_clips = []
        for j, frame in enumerate(sentence_clip.iter_frames(fps=24, dtype='uint8')):
            frame_image = Image.fromarray(frame)
            if method == 'zoom':
                frame_image = resize_to_aspect_ratio_with_zoom(frame_image, 9 / 16, (1080, 1920))
            else:
                frame_image = stretch_vertically_to_resolution(frame_image, (1080, 1920))

            frame_with_text = add_centered_text_with_outline(frame_image.copy(), sentence, font_path, font_size,
                                                             text_color)
            frame_clips.append(np.array(frame_with_text))

        if frame_clips:
            text_clip = ImageSequenceClip(frame_clips, fps=24)
            clips.append(text_clip)

    if clips:
        final_clip = concatenate_videoclips(clips, method="compose")
        final_clip.write_videofile(output_video_path, codec='libx264', bitrate="5000k", fps=24)
    else:
        print("No clips were created.")

def create_video_from_media_with_text(input_path, output_video_path, text, font_path, font_size, text_color,
                                      total_duration, method='zoom'):
    if os.path.splitext(input_path)[1].lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
        create_video_from_image_with_text(input_path, output_video_path, text, font_path, font_size, text_color,
                                          total_duration, method)
    elif os.path.splitext(input_path)[1].lower() in ['.mp4', '.mov', '.avi', '.mkv', '.wmv']:
        create_video_from_video_with_text(input_path, output_video_path, text, font_path, font_size, text_color,
                                          total_duration, method)
    else:
        raise ValueError("Unsupported file format")

def main():
    input_path = r'_6d8f63a5-e67a-487b-b926-dac923c76933.jpg'  # Path to your input video
    output_video_path = 'output_video.mp4'  # Path to save the output video as MP4
    text = 'A Man Who is Master in Patience, is Master in Everything. Here is another sentence! What about this one?'
    font_path = r'R:\Windows\Img2Video\Fonts\English\Roboto-BoldItalic.ttf'  # Use raw string for font path
    font_size = 50  # Font size
    text_color = (0, 0, 0)  # Text color in RGB
    total_duration = 15  # Total duration for the video

    # Prompt user for the output method
    print("Choose the output method:")
    print("1: Select this for ALL TYPES OF IMAGES and HORIZONTAL VIDEOS")
    print("2: Select this if you've selected a VERTICAL VIDEO")
    choice = input("Enter 1 or 2: ")

    method = 'zoom' if choice == '1' else 'stretch' if choice == '2' else 'zoom'

    create_video_from_media_with_text(input_path, output_video_path, text, font_path, font_size, text_color,
                                      total_duration, method)

if __name__ == "__main__":
    main()