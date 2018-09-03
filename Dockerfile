FROM python:2.7.15-slim-stretch

COPY ./dat_files /tmp
COPY ./dist/gisst-0.1.0.tar.gz /tmp
COPY ./test_files /tmp

RUN apt-get update && apt-get install -y --no-install-recommends wget \
     && mkdir /tmp/ucon64 && cd /tmp/ucon64 \
    # Install Ucon64 dependency from pre-compiled binary, may just include this going forward
     && wget -O ucon64-2.1.0-linux-x86_64-bin.tar.gz http://sourceforge.net/projects/ucon64/files/ucon64/ucon64-2.1.0/ucon64-2.1.0-linux-x86_64-bin.tar.gz/download \
     && tar -xvf ucon64-2.1.0-linux-x86_64-bin.tar.gz \
     && cp ucon64-2.1.0-linux-x86_64-bin/ucon64 /usr/local/bin/ \
     && cd /tmp && rm -rf ucon64 \
    # Install Ucon64 current dependent DAT files
     && mkdir -p /root/.ucon64/dat \
     && cp /tmp/*.dat /root/.ucon64/dat \
     && rm /tmp/*.dat \
     && ucon64 -db \
     \
    # Setup python environment for CLI
     && pip install /tmp/gisst-0.1.0.tar.gz \
     && rm /tmp/gisst-0.1.0.tar.gz \
    # Setup data storage 
     && mkdir /.gisst

VOLUME /.gisst

ENTRYPOINT ["gisst"]

    
