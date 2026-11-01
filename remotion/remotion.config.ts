import { Config } from "@remotion/cli/config";

// Frames as JPEG keep the render fast; the H.264 output is what platforms re-encode anyway.
Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(92);
Config.setCodec("h264");
Config.setCrf(18);
Config.setPixelFormat("yuv420p");
