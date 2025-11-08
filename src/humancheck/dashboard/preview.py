"""Preview panel components for Streamlit dashboard."""
from typing import List

import streamlit as st


def render_preview_panel(attachments: List):
    """
    Render preview panel for attachments.

    Args:
        attachments: List of Attachment objects
    """
    if not attachments:
        st.info("No attachments available")
        return

    # Attachment selector
    if len(attachments) > 1:
        selected_idx = st.selectbox(
            "Select attachment",
            range(len(attachments)),
            format_func=lambda i: attachments[i].file_name or f"Attachment {i + 1}",
        )
        attachment = attachments[selected_idx]
    else:
        attachment = attachments[0]

    # Render based on category
    category = attachment.content_category

    if category == "text":
        render_text_preview(attachment)
    elif category == "image":
        render_image_preview(attachment)
    elif category == "audio":
        render_audio_preview(attachment)
    elif category == "video":
        render_video_preview(attachment)
    elif category == "document":
        render_document_preview(attachment)
    else:
        st.warning(f"Unsupported content type: {attachment.content_type}")

    # Metadata
    with st.expander("Metadata"):
        metadata_display = {
            "File Name": attachment.file_name,
            "Content Type": attachment.content_type,
            "File Size": f"{attachment.file_size / 1024:.2f} KB",
            "Uploaded": attachment.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if attachment.checksum:
            metadata_display["Checksum (SHA256)"] = attachment.checksum
        if attachment.file_metadata:
            metadata_display.update(attachment.file_metadata)

        st.json(metadata_display)


def render_text_preview(attachment):
    """Render text content with syntax highlighting."""
    st.subheader("📝 Text Content")

    content = attachment.inline_content

    if not content:
        st.warning("Text content not available for preview")
        return

    # Detect language for syntax highlighting
    language = "text"
    if attachment.file_metadata:
        language = attachment.file_metadata.get("language", "text")

    # Try to detect from filename
    if attachment.file_name:
        if attachment.file_name.endswith(".py"):
            language = "python"
        elif attachment.file_name.endswith(".js"):
            language = "javascript"
        elif attachment.file_name.endswith(".json"):
            language = "json"
        elif attachment.file_name.endswith(".md"):
            language = "markdown"
        elif attachment.file_name.endswith(".yaml") or attachment.file_name.endswith(".yml"):
            language = "yaml"
        elif attachment.file_name.endswith(".sql"):
            language = "sql"

    # Determine if code or markdown
    if language in ["python", "javascript", "java", "sql", "yaml", "json"]:
        st.code(content, language=language)
    elif language == "markdown":
        st.markdown(content)
    else:
        st.text_area("Content", content, height=400, disabled=True)

    # Word count
    word_count = len(content.split())
    st.caption(f"Word count: {word_count}")


def render_image_preview(attachment):
    """Render image with download option."""
    st.subheader("🖼️ Image Preview")

    # Show image using download URL
    if attachment.download_url:
        # For local storage, construct the full API URL
        api_url = f"http://localhost:8000{attachment.download_url}"
        st.image(
            api_url,
            caption=attachment.description or attachment.file_name,
            use_container_width=True,
        )

        # Image info
        if attachment.file_metadata:
            cols = st.columns(4)
            if "width" in attachment.file_metadata and "height" in attachment.file_metadata:
                cols[0].metric("Dimensions", f"{attachment.file_metadata['width']}×{attachment.file_metadata['height']}")
            if "size_bytes" in attachment.file_metadata:
                size_mb = attachment.file_metadata["size_bytes"] / (1024 * 1024)
                cols[1].metric("Size", f"{size_mb:.2f} MB")
            if "format" in attachment.file_metadata:
                cols[2].metric("Format", attachment.file_metadata["format"])

        # Download button
        if st.button("Download Original", key=f"download_{attachment.id}"):
            st.markdown(f"[Download]({api_url})", unsafe_allow_html=True)


def render_audio_preview(attachment):
    """Render audio player."""
    st.subheader("🎵 Audio Preview")

    if attachment.download_url:
        # For local storage, construct the full API URL
        api_url = f"http://localhost:8000{attachment.download_url}"

        st.audio(api_url, format=attachment.content_type)

        # Audio info
        if attachment.file_metadata:
            cols = st.columns(3)
            if "duration_seconds" in attachment.file_metadata:
                duration = attachment.file_metadata["duration_seconds"]
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                cols[0].metric("Duration", f"{minutes}:{seconds:02d}")
            if "sample_rate" in attachment.file_metadata:
                cols[1].metric("Sample Rate", f"{attachment.file_metadata['sample_rate']} Hz")
            if "bitrate" in attachment.file_metadata:
                cols[2].metric("Bitrate", f"{attachment.file_metadata['bitrate']} kbps")


def render_video_preview(attachment):
    """Render video player."""
    st.subheader("🎥 Video Preview")

    if attachment.download_url:
        # For local storage, construct the full API URL
        api_url = f"http://localhost:8000{attachment.download_url}"

        st.video(api_url)

        # Video info
        if attachment.file_metadata:
            cols = st.columns(4)
            if "duration_seconds" in attachment.file_metadata:
                duration = attachment.file_metadata["duration_seconds"]
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                cols[0].metric("Duration", f"{minutes}:{seconds:02d}")
            if "resolution" in attachment.file_metadata:
                cols[1].metric("Resolution", attachment.file_metadata["resolution"])
            if "fps" in attachment.file_metadata:
                cols[2].metric("FPS", f"{attachment.file_metadata['fps']}")
            if "codec" in attachment.file_metadata:
                cols[3].metric("Codec", attachment.file_metadata["codec"])


def render_document_preview(attachment):
    """Render PDF document."""
    st.subheader("📄 Document Preview")

    if attachment.download_url:
        # For local storage, construct the full API URL
        api_url = f"http://localhost:8000{attachment.download_url}"

        # Use iframe for PDF
        st.markdown(
            f'<iframe src="{api_url}" width="100%" height="800px"></iframe>',
            unsafe_allow_html=True,
        )

        # Document info
        if attachment.file_metadata and "page_count" in attachment.file_metadata:
            st.caption(f"Pages: {attachment.file_metadata['page_count']}")
