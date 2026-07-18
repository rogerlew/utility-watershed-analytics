ARG SOURCE_DATE_EPOCH=0

FROM python:3.12.9-slim-bookworm@sha256:48a11b7ba705fd53bf15248d1f94d36c39549903c5d59edcfa2f3f84126e7b44

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/release-tool

WORKDIR /work

COPY --chown=65532:65532 release-tool/uwa_release_tool/cli.py /usr/local/bin/data-release.py

USER 65532:65532

ENTRYPOINT ["python3", "/usr/local/bin/data-release.py"]
CMD ["status"]
