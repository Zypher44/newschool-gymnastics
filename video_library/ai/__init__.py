"""Load the computer-vision runtime only in processing workers."""

def __getattr__(name):
    if name == 'VideoAnalysisProcessor':
        from .processor import VideoAnalysisProcessor
        return VideoAnalysisProcessor
    raise AttributeError(name)

__all__ = ['VideoAnalysisProcessor']
