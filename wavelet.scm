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
                (gimp-image-convert-grayscale image)
                (gimp-invert 2)
                (define newFilename (string-append
                    (substring filename 0 (- (string-length filename) 4))
                    ".png"
                                
                ))
                (file-png-save RUN-NONINTERACTIVE
                    image drawable newFilename newFilename
                    FALSE 0 FALSE FALSE FALSE FALSE FALSE)
                (gimp-image-delete image))
                (set! filelist (cdr filelist)))))
