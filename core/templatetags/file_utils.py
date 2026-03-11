from django import template
import os

register = template.Library()

@register.filter
def file_icon(filename):
    """Return appropriate icon class based on file extension"""
    ext = os.path.splitext(filename)[1].lower()
    
    icons = {
        '.pdf': 'fa-file-pdf text-red-600',
        '.doc': 'fa-file-word text-blue-600',
        '.docx': 'fa-file-word text-blue-600',
        '.xls': 'fa-file-excel text-green-600',
        '.xlsx': 'fa-file-excel text-green-600',
        '.ppt': 'fa-file-powerpoint text-orange-600',
        '.pptx': 'fa-file-powerpoint text-orange-600',
        '.txt': 'fa-file-alt text-gray-600',
        '.zip': 'fa-file-archive text-purple-600',
        '.rar': 'fa-file-archive text-purple-600',
        '.jpg': 'fa-file-image text-indigo-600',
        '.jpeg': 'fa-file-image text-indigo-600',
        '.png': 'fa-file-image text-indigo-600',
        '.gif': 'fa-file-image text-indigo-600',
        '.mp4': 'fa-file-video text-indigo-600',
        '.mov': 'fa-file-video text-indigo-600',
        '.avi': 'fa-file-video text-indigo-600',
    }
    
    return icons.get(ext, 'fa-file text-gray-600')

@register.filter
def file_color(filename):
    """Return appropriate background color class based on file extension"""
    ext = os.path.splitext(filename)[1].lower()
    
    colors = {
        '.pdf': 'bg-red-100',
        '.doc': 'bg-blue-100',
        '.docx': 'bg-blue-100',
        '.xls': 'bg-green-100',
        '.xlsx': 'bg-green-100',
        '.ppt': 'bg-orange-100',
        '.pptx': 'bg-orange-100',
        '.txt': 'bg-gray-100',
        '.zip': 'bg-purple-100',
        '.rar': 'bg-purple-100',
    }
    
    return colors.get(ext, 'bg-indigo-100')

@register.filter
def filename(value):
    """Return only the filename from a full path"""
    return os.path.basename(value)