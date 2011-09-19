; GIMP - The GNU Image Manipulation Program
; wavelet script - Copyright (C) 2011 Art Rhyno http://projectconifer.ca
;

(define (batch-wavelet-enhance pattern
    amount
    radius
    luminance)
    (let* ((filelist (cadr (file-glob pattern 1))))
        (while (not (null? filelist))
            (let* ((filename (car filelist))
                (image (car (gimp-file-load RUN-NONINTERACTIVE
                    filename filename)))
                (drawable (car (gimp-image-get-active-layer image))))
                (plug-in-wavelet-sharpen RUN-NONINTERACTIVE
                    image drawable amount radius luminance)
                (gimp-invert drawable)
                (define newFilename (string-append
                    (substring filename 0 (- (string-length filename) 4))
                    ".jpg"
                                
                ))
                (file-jpeg-save RUN-NONINTERACTIVE
                    image drawable newFilename newFilename 
                    0.75 0 1 0 "ossocr" 0 1 0 0 )
                    ; 0.75 quality (float 0 <= x <= 1)
                    ;      0 smoothing factor (0 <= x <= 1)
                    ;        1 optimization of entropy encoding parameter (0/1)
                    ;          1 enable progressive jpeg image loading (0/1)
                    ;            "xxxx"  image comment
                    ;                   0 subsampling option number
                    ;                     1 force creation of a baseline JPEG
                    ;                       0 frequency of restart markers 
                    ;                         in rows, 0 = no restart markers
                    ;                         0 DCT algoritm to use 
                (gimp-image-delete image))
                (set! filelist (cdr filelist)))))
