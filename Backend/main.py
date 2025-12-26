def pipeline():

    from download_video import VideoDownloader
    from detect_video_audio import gen_json
    from ingest_and_query_chroma import VectorDB
    from ExplainX_LLM import LLM

    link=input("Enter video link: ").strip()
    name = VideoDownloader(link).yt_download()
    print("Video Name:",name)
    if not name:
        print("Video download failed. Exiting.")
        exit()

    obj_json = gen_json(name)
    obj_json.main()
    obj_db=VectorDB(name)
    obj_db.ingest_json()
    answer=LLM().summarize_video(name)
    print("--------------------------------------------")
    print("Video Summary:\n",answer)
    print("--------------------------------------------")

if __name__ == "__main__":
    pipeline()




