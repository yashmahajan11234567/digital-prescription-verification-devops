package com.rxverify;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class AppTest {
    @Test
    void testGetAppName() {
        assertEquals("RxVerify", App.getAppName());
    }

    @Test
    void testGetVersion() {
        assertEquals("1.0.0", App.getVersion());
    }

    @Test
    void testAdd() {
        assertEquals(3, App.add(1, 2));
        assertEquals(-1, App.add(2, -3));
        assertEquals(0, App.add(0, 0));
    }

    @Test
    void testMainRunsWithoutException() {
        // Just verify main doesn't throw
        App.main(new String[]{});
    }
}