package com.rxverify;

public class App {
    public static void main(String[] args) {
        System.out.println("RxVerify Maven Demo - Build Successful!");
        System.out.println("Version: 1.0.0");
        System.out.println("Application: Digital Prescription Verification System");
    }

    public static String getAppName() {
        return "RxVerify";
    }

    public static String getVersion() {
        return "1.0.0";
    }

    public static int add(int a, int b) {
        return a + b;
    }
}