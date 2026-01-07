"""Track image handling utilities."""
import os
import discord
from config import IMG_DIR


def normalize_track_name(track_name: str) -> str:
    """Normalize track name for matching (lowercase, handle spaces/underscores)."""
    return track_name.lower().strip().replace(" ", "_")


def find_track_image(track_name: str) -> tuple[str, discord.File] | tuple[None, None]:
    """Find matching image file for a track name. Returns (filename, File) or (None, None)."""
    if not os.path.exists(IMG_DIR):
        return None, None
    
    # Normalize track name for matching
    normalized_track = normalize_track_name(track_name)
    
    # Get all image files
    image_files = [f for f in os.listdir(IMG_DIR) 
                   if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
    
    # Try exact match first (case-insensitive)
    for img_file in image_files:
        normalized_img = normalize_track_name(os.path.splitext(img_file)[0])
        if normalized_track == normalized_img:
            file_path = os.path.join(IMG_DIR, img_file)
            return img_file, discord.File(file_path, filename=img_file)
    
    # Try partial match (track name contained in image name or vice versa)
    for img_file in image_files:
        normalized_img = normalize_track_name(os.path.splitext(img_file)[0])
        # Remove common prefixes/suffixes for matching
        img_clean = normalized_img.replace("circuit", "").replace("gp", "").replace("_", "").strip()
        track_clean = normalized_track.replace("_", "").strip()
        
        if track_clean in img_clean or img_clean in track_clean:
            file_path = os.path.join(IMG_DIR, img_file)
            return img_file, discord.File(file_path, filename=img_file)
    
    # Special case mappings for common variations
    special_mappings = {
        "spa": "Spa-Francochamps.jpg",
        "nurburgring": "Nürburgring.jpeg",
        "nurburgring_24h": "Nürburgring.jpeg",
        "paul_ricard": "Circuit Paul Ricard.jpg",
        "zandvoort": "Circuit Zandvoort.jpg",
        "zolder": "Circuit Zolder.jpg",
        "brands_hatch": "Brands Hatch GP.jpg",
        "cota": "Circuit of the Americas.jpg",
        "valencia": "Circuit Ricardo Tormo.jpg",
        "red_bull_ring": "Red Bull Ring.jpg",
        "mount_panorama": "Mount Panorama Circuit.jpg",
        "silverstone": "Silverstone GP Circuit.jpg",
        "donington": "Donington Park.jpg",
        "oulton_park": "Oulton Park.jpg",
        "watkins_glen": "Watkins Glen.jpg",
        "suzuka": "Suzuka Circuit.jpg",
    }
    
    if normalized_track in special_mappings:
        img_file = special_mappings[normalized_track]
        file_path = os.path.join(IMG_DIR, img_file)
        if os.path.exists(file_path):
            return img_file, discord.File(file_path, filename=img_file)
    
    return None, None

